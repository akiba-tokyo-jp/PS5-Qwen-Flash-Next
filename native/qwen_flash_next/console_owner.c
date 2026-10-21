/* SPDX-License-Identifier: MIT
 * Metadata inspection and one ordinary OS title-close request.
 * No signals, GPU operations, registration changes or restart operations.
 */
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <sys/user.h>
#include <unistd.h>

typedef struct { uint32_t app_id; uint64_t reserved; char title_id[14]; char tail[0x3c]; } app_info;
_Static_assert(sizeof(app_info) == 96 && offsetof(app_info, title_id) == 16, "AppInfo ABI");
int sceKernelGetAppInfo(int, app_info *);
int sceSystemServiceGetAppId(const char *);
int sceSystemServiceGetAppIdOfRunningBigApp(void);
int sceSystemServiceKillApp(int, int, int, int);

static int snapshot(int pid, struct kinfo_proc *proc, app_info *app) {
    struct { uint64_t before[2]; unsigned char bytes[4096]; uint64_t after[2]; } p;
    memset(&p, 0, sizeof(p));
    p.before[0] = p.before[1] = p.after[0] = p.after[1] = UINT64_C(0x6a7b83c44d29e510);
    size_t size = sizeof(p.bytes);
    int mib[] = { CTL_KERN, KERN_PROC, KERN_PROC_PID, pid };
    if (sysctl(mib, 4, p.bytes, &size, NULL, 0) || size != sizeof(*proc) ||
        p.before[0] != p.before[1] || p.before[0] != p.after[0] || p.before[0] != p.after[1] ||
        p.before[0] != UINT64_C(0x6a7b83c44d29e510)) return 0;
    memcpy(proc, p.bytes, sizeof(*proc));
    if (proc->ki_structsize != sizeof(*proc) || proc->ki_pid != pid || proc->ki_uid != 1 ||
        !memchr(proc->ki_comm, 0, sizeof(proc->ki_comm)) || strcmp(proc->ki_comm, "eboot.bin")) return 0;
    struct { uint64_t before; app_info value; uint64_t after; } a;
    memset(&a, 0, sizeof(a)); a.before = a.after = UINT64_C(0x5af1932e74168c02);
    if (sceKernelGetAppInfo(pid, &a.value) || a.before != a.after || a.before != UINT64_C(0x5af1932e74168c02)) return 0;
    if (!memchr(a.value.title_id, 0, sizeof(a.value.title_id)) || strncmp(a.value.title_id, "PPSA", 4) ||
        strlen(a.value.title_id) != 9 || !a.value.app_id || a.value.app_id > INT32_MAX ||
        sceSystemServiceGetAppId(a.value.title_id) != (int)a.value.app_id ||
        sceSystemServiceGetAppIdOfRunningBigApp() != (int)a.value.app_id) return 0;
    *app = a.value;
    return 1;
}

static int64_t number(const char *text) {
    char *end = NULL; errno = 0;
    int64_t value = strtoll(text, &end, 10);
    return errno || !*text || *end || value < 0 ? -1 : value;
}

static int owned_path(const char *text) {
    return !strncmp(text, "/data/ai/qwen-", 14) && !strstr(text, "..") && !strchr(text, '\n');
}

int main(int argc, char **argv) {
    int inspect = argc == 4 && !strcmp(argv[1], "--inspect");
    int closing = argc == 9 && !strcmp(argv[1], "--close");
    if (!inspect && !closing) return 2;
    int64_t pid64 = number(argv[2]);
    const char *log_path = inspect ? argv[3] : argv[7];
    if (pid64 <= 0 || pid64 > INT32_MAX || !owned_path(log_path) || (closing && !owned_path(argv[8]))) return 2;
    int fd = open(log_path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0644);
    if (fd < 0) return 3;
    FILE *log = fdopen(fd, "w");
    if (!log) { close(fd); return 3; }
    int status = 1, requested = 0, rc = -1;
    struct kinfo_proc a, b; app_info aa, ab;
    if (!snapshot((int)pid64, &a, &aa) || !snapshot((int)pid64, &b, &ab) ||
        a.ki_start.tv_sec != b.ki_start.tv_sec || a.ki_start.tv_usec != b.ki_start.tv_usec ||
        aa.app_id != ab.app_id || strcmp(aa.title_id, ab.title_id)) goto end;
    fprintf(log, "OWNER pid=%d start_sec=%lld start_usec=%lld app_id=%u title=%s\n",
            a.ki_pid, (long long)a.ki_start.tv_sec, (long long)a.ki_start.tv_usec, aa.app_id, aa.title_id);
    if (fflush(log) || fsync(fd)) goto end;
    if (inspect) { status = 0; goto end; }
    if (number(argv[3]) != a.ki_start.tv_sec || number(argv[4]) != a.ki_start.tv_usec ||
        strcmp(argv[5], aa.title_id) || number(argv[6]) != aa.app_id) goto end;
    int once = open(argv[8], O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (once < 0) goto end;
    static const char intent[] = "One ordinary OS title-close request; no automatic retry.\n";
    int once_ok = write(once, intent, sizeof(intent)-1) == sizeof(intent)-1 && !fsync(once);
    if (close(once)) once_ok = 0;
    if (!once_ok || !snapshot((int)pid64, &b, &ab) || b.ki_start.tv_sec != a.ki_start.tv_sec ||
        b.ki_start.tv_usec != a.ki_start.tv_usec || ab.app_id != aa.app_id || strcmp(ab.title_id, aa.title_id)) goto end;
    fprintf(log, "BEFORE ordinary_OS_close app_id=%u calls=1 signals=0 GPU_calls=0\n", aa.app_id);
    if (fflush(log) || fsync(fd)) goto end;
    requested = 1;
    rc = sceSystemServiceKillApp((int)aa.app_id, -1, 0, 0);
    status = rc == 0 ? 0 : 1;
end:
    fprintf(log, "END success=%d close_calls=%d return_code=0x%08x PID_absence_proven=0\n", status == 0, requested, (unsigned)rc);
    if (fflush(log) || fsync(fd)) status = 1;
    if (fclose(log)) status = 1;
    return status;
}
