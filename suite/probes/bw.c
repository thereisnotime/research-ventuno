// Multi-threaded memory read/copy bandwidth, STREAM-style. Usage: bw <threads> <MB per thread> <reps>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static size_t N; static int REPS;
typedef struct { uint64_t *a, *b; uint64_t sum; int mode; } job_t;

static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

static void *run(void *p) {
    job_t *j = p; uint64_t s = 0;
    for (int r = 0; r < REPS; r++) {
        if (j->mode == 0) { for (size_t i = 0; i < N; i += 4) s += j->a[i] + j->a[i+1] + j->a[i+2] + j->a[i+3]; }
        else memcpy(j->b, j->a, N * 8);
    }
    j->sum = s; return NULL;
}

int main(int argc, char **argv) {
    int T = argc > 1 ? atoi(argv[1]) : 4; size_t mb = argc > 2 ? atol(argv[2]) : 256; REPS = argc > 3 ? atoi(argv[3]) : 10;
    N = mb * 1024 * 1024 / 8;
    for (int mode = 0; mode < 2; mode++) {
        pthread_t th[64]; job_t js[64];
        for (int t = 0; t < T; t++) {
            js[t].a = aligned_alloc(64, N * 8); js[t].b = mode ? aligned_alloc(64, N * 8) : NULL; js[t].mode = mode;
            memset(js[t].a, t + 1, N * 8); if (mode) memset(js[t].b, 0, N * 8);
        }
        double t0 = now();
        for (int t = 0; t < T; t++) pthread_create(&th[t], NULL, run, &js[t]);
        for (int t = 0; t < T; t++) pthread_join(th[t], NULL);
        double dt = now() - t0;
        double bytes = (double) T * REPS * N * 8 * (mode ? 2 : 1);   // copy = read + write
        printf("%s threads=%d %.1f GB/s\n", mode ? "copy" : "read", T, bytes / dt / 1e9);
        for (int t = 0; t < T; t++) { free(js[t].a); free(js[t].b); }
    }
    return 0;
}
