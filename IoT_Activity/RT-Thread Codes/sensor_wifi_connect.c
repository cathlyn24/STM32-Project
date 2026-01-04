#include <rtthread.h>
#include <rtdevice.h>
#include <board.h>
#include "icm20608.h"
#include <webclient.h>
#include <cjson_util.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <sys/socket.h>

/* WIFI CONFIGURATION */
#define WIFI_SSID        "DITOHOME_D9175"
#define WIFI_PASSWORD    "2hXHL7g5E5"

/* CLOUD CONFIGURATION */
#define API_URL "http://cathlynramo.pythonanywhere.com/api/data"

/* DEFINES */
#define THREAD_PRIORITY         25
#define THREAD_STACK_SIZE       8192
#define THREAD_TIMESLICE        5

/* GLOBAL VARIABLES */
icm20608_device_t dev = RT_NULL;

/* DATA UPLOAD FUNCTION - Using Raw Sockets */
static void upload_data(float ax, float ay, float az, float gx, float gy, float gz, char *label)
{
    int sock = -1;
    struct sockaddr_in server_addr;
    struct hostent *host;
    char request[1024];
    char response[512];
    int ret;

    // Create JSON
    cJSON *root = cJSON_CreateObject();
    cJSON_AddNumberToObject(root, "ax", ax);
    cJSON_AddNumberToObject(root, "ay", ay);
    cJSON_AddNumberToObject(root, "az", az);
    cJSON_AddNumberToObject(root, "gx", gx);
    cJSON_AddNumberToObject(root, "gy", gy);
    cJSON_AddNumberToObject(root, "gz", gz);
    cJSON_AddStringToObject(root, "label", label);

    char *json_data = cJSON_PrintUnformatted(root);
    int json_length = rt_strlen(json_data);

    rt_kprintf("Sending: %s\n", json_data);

    // Resolve hostname
    host = gethostbyname("cathlynramo.pythonanywhere.com");
    if (host == RT_NULL) {
        rt_kprintf("ERROR: DNS resolution failed\n");
        goto cleanup;
    }

    rt_kprintf("DNS OK: %s\n", inet_ntoa(*(struct in_addr*)host->h_addr));

    // Create socket
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        rt_kprintf("ERROR: Socket creation failed\n");
        goto cleanup;
    }

    // Set up server address
    rt_memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(80);
    rt_memcpy(&server_addr.sin_addr, host->h_addr, host->h_length);

    // Connect to server
    ret = connect(sock, (struct sockaddr *)&server_addr, sizeof(server_addr));
    if (ret < 0) {
        rt_kprintf("ERROR: Connection failed (ret=%d)\n", ret);
        goto cleanup;
    }

    rt_kprintf("Connected to server\n");

    // Build HTTP POST request
    rt_snprintf(request, sizeof(request),
                "POST /api/data HTTP/1.1\r\n"
                "Host: cathlynramo.pythonanywhere.com\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: %d\r\n"
                "Connection: close\r\n"
                "\r\n"
                "%s", json_length, json_data);

    // Send request
    int total_sent = 0;
    int request_len = rt_strlen(request);
    while (total_sent < request_len) {
        int sent = send(sock, request + total_sent, request_len - total_sent, 0);
        if (sent <= 0) {
            rt_kprintf("ERROR: Send failed\n");
            goto cleanup;
        }
        total_sent += sent;
    }

    rt_kprintf("Sent %d bytes\n", total_sent);

    // Receive response
    rt_memset(response, 0, sizeof(response));
    int received = recv(sock, response, sizeof(response) - 1, 0);
    if (received > 0) {
        response[received] = '\0';
        rt_kprintf("Response: %s\n", response);

        // Check for 200 OK
        if (rt_strstr(response, "200 OK") != RT_NULL) {
            rt_kprintf("SUCCESS: 200 OK\n");
        } else {
            rt_kprintf("FAILURE: Non-200 response\n");
        }
    } else {
        rt_kprintf("ERROR: No response received (ret=%d)\n", received);
    }

cleanup:
    if (sock >= 0) {
        closesocket(sock);
    }
    if (json_data) {
        cJSON_free(json_data);
    }
    cJSON_Delete(root);
}

/* MAIN SENSOR THREAD */
static void sensor_thread_entry(void *parameter)
{
    rt_int16_t acc_x, acc_y, acc_z;
    rt_int16_t gyro_x, gyro_y, gyro_z;

    dev = icm20608_init("i2c2");
    if (dev == RT_NULL) {
        rt_kprintf("ICM20608 Init Failed!\n");
        return;
    }

    rt_kprintf("ICM20608 Initialized Successfully!\n");

    while (1) {
        icm20608_get_accel(dev, &acc_x, &acc_y, &acc_z);
        icm20608_get_gyro(dev, &gyro_x, &gyro_y, &gyro_z);

        rt_kprintf("\n--- Sensor Reading ---\n");
        rt_kprintf("Accel: x=%d, y=%d, z=%d\n", acc_x, acc_y, acc_z);
        rt_kprintf("Gyro: x=%d, y=%d, z=%d\n", gyro_x, gyro_y, gyro_z);

        upload_data((float)acc_x, (float)acc_y, (float)acc_z,
                    (float)gyro_x, (float)gyro_y, (float)gyro_z, "walking");

        rt_thread_mdelay(2000);
    }
}

int main(void)
{
    /* 1. Connect to Wi-Fi */
    rt_kprintf("\n>>> Connecting to Wi-Fi...\n");
    rt_wlan_connect(WIFI_SSID, WIFI_PASSWORD);

    while(rt_wlan_is_ready() != RT_TRUE) {
        rt_thread_mdelay(100);
    }
    rt_kprintf("Wi-Fi Connected!\n");

    /* 2. Wait for DHCP and network stack */
    rt_kprintf("Waiting for network to stabilize...\n");
    rt_thread_mdelay(3000);

    /* 3. Set DNS */
    extern int set_dns(const char *dns_server);
    set_dns("8.8.8.8");
    rt_kprintf("DNS Set to 8.8.8.8\n");

    /* 4. Test DNS resolution */
    rt_thread_mdelay(1000);
    struct hostent *host = gethostbyname("cathlynramo.pythonanywhere.com");
    if (host) {
        rt_kprintf("DNS Pre-check OK: %s\n", inet_ntoa(*(struct in_addr*)host->h_addr));
    } else {
        rt_kprintf("WARNING: DNS pre-check failed!\n");
    }

    /* 5. Final wait before starting */
    rt_kprintf("\n>>> Starting sensor thread in 2 seconds...\n");
    rt_thread_mdelay(2000);

    /* 6. Start sensor thread */
    rt_thread_t tid = rt_thread_create("sensor",
                                       sensor_thread_entry,
                                       RT_NULL,
                                       THREAD_STACK_SIZE,
                                       THREAD_PRIORITY,
                                       THREAD_TIMESLICE);
    if (tid != RT_NULL) {
        rt_thread_startup(tid);
        rt_kprintf("Sensor thread started successfully!\n");
    } else {
        rt_kprintf("ERROR: Failed to create sensor thread!\n");
    }

    return 0;
}

