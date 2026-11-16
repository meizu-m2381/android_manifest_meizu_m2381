#include <media/stagefright/bqhelper/GraphicBufferSource.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
int main() {
 android::sp<android::GraphicBufferSource> source = new android::GraphicBufferSource;
 if (source->initCheck() != android::OK) { puts("FAIL initCheck"); return 1; }
 auto p1 = source->getHGraphicBufferProducer_V1_0();
 auto p2 = source->getHGraphicBufferProducer();
 if (!p1 || !p2) { puts("FAIL HIDL producers"); return 2; }
 Dl_info info = {};
 auto* fn = dlsym(RTLD_DEFAULT, "_ZNK7android19GraphicBufferSource25getHGraphicBufferProducerEv");
 if (!fn || !dladdr(fn, &info) || !strstr(info.dli_fname, "/libstagefright_bufferqueue_helper-v33.so")) return 3;
 printf("PASS API33 layout/initCheck/HIDL1/HIDL2 provider=%s\n", info.dli_fname);
 return 0;
}
