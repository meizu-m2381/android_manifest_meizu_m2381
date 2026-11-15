// SPDX-License-Identifier: Apache-2.0
// Standalone device probe. No Android headers needed; link against built
// bionic. Test actual pixels as well as context creation: split driver
// instances may report success while dispatching GL calls to a no-op table.
typedef void *Ptr;
typedef unsigned int U;
typedef int I;
extern int printf(const char *, ...);
extern int fflush(void *);
extern void *dlopen(const char *, int);
extern void *dlsym(void *, const char *);
extern char *dlerror(void);
#define FN(ret, name, args) ret(*name) args = (ret(*) args)dlsym(egl, #name)
int main(void) {
  int passed = 0;
  void *egl = dlopen("libEGL.so", 2), *gl = dlopen("libGLESv2.so", 2);
  if (!egl || !gl) {
    printf("dlopen: %s\n", dlerror());
    return 2;
  }
  FN(Ptr, eglGetDisplay, (Ptr));
  FN(U, eglInitialize, (Ptr, I *, I *));
  FN(const char *, eglQueryString, (Ptr, I));
  FN(U, eglChooseConfig, (Ptr, const I *, Ptr *, I, I *));
  FN(Ptr, eglCreateContext, (Ptr, Ptr, Ptr, const I *));
  FN(Ptr, eglCreatePbufferSurface, (Ptr, Ptr, const I *));
  FN(U, eglMakeCurrent, (Ptr, Ptr, Ptr, Ptr));
  FN(U, eglDestroyContext, (Ptr, Ptr));
  FN(U, eglDestroySurface, (Ptr, Ptr));
  FN(I, eglGetError, (void));
  const unsigned char *(*glGetString)(U) = dlsym(gl, "glGetString");
  void (*glClearColor)(float, float, float, float) = dlsym(gl, "glClearColor");
  void (*glClear)(U) = dlsym(gl, "glClear");
  void (*glReadPixels)(I, I, I, I, U, U, void *) = dlsym(gl, "glReadPixels");
  U (*glGetError)(void) = dlsym(gl, "glGetError");
  Ptr d = eglGetDisplay(0);
  I major = 0, minor = 0;
  if (!eglInitialize(d, &major, &minor)) {
    printf("eglInitialize error=%x\n", eglGetError());
    return 3;
  }
  printf("EGL %d.%d vendor=%s version=%s\nEXT=%s\n", major, minor,
         eglQueryString(d, 0x3053), eglQueryString(d, 0x3054),
         eglQueryString(d, 0x3055));
  fflush(0);
  int versions[][2] = {{2, 0}, {3, 0}, {3, 1}, {3, 2}};
  for (int k = 0; k < 4; k++) {
    I attrs[] = {0x3033, 1,      0x3040, k ? 0x40 : 4, 0x3024, 8, 0x3023,
                 8,      0x3022, 8,      0x3038};
    Ptr cfg = 0;
    I n = 0;
    U ok = eglChooseConfig(d, attrs, &cfg, 1, &n);
    printf("ES%d.%d choose=%u count=%d err=%x\n", versions[k][0],
           versions[k][1], ok, n, eglGetError());
    fflush(0);
    if (!ok || !n)
      continue;
    I ca[] = {0x3098, versions[k][0], 0x30fb, versions[k][1], 0x3038};
    Ptr c = eglCreateContext(d, cfg, 0, ca);
    printf("context=%p err=%x\n", c, eglGetError());
    fflush(0);
    if (!c)
      continue;
    I sa[] = {0x3057, 16, 0x3056, 16, 0x3038};
    Ptr s = eglCreatePbufferSurface(d, cfg, sa);
    ok = eglMakeCurrent(d, s, s, c);
    printf("surface=%p current=%u err=%x\n", s, ok, eglGetError());
    fflush(0);
    if (ok) {
      unsigned char px[4] = {0};
      printf("GL vendor=%s renderer=%s version=%s\n", glGetString(0x1f00),
             glGetString(0x1f01), glGetString(0x1f02));
      glClearColor(.25f, .5f, .75f, 1);
      glClear(0x4000);
      glReadPixels(0, 0, 1, 1, 0x1908, 0x1401, px);
      U err = glGetError();
      printf("pixel=%u,%u,%u,%u glerr=%x\n", px[0], px[1], px[2], px[3], err);
      if (px[0] == 64 && px[1] == 128 && px[2] == 191 && px[3] == 255 && !err)
        passed++;
      fflush(0);
    }
    eglMakeCurrent(d, 0, 0, 0);
    eglDestroySurface(d, s);
    eglDestroyContext(d, c);
  }
  printf("PASS_COUNT=%d/4\n", passed);
  return passed == 4 ? 0 : 1;
}
