#include <android-base/file.h>
#include <android-base/unique_fd.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include <unistd.h>
namespace android::base {
std::string Trim(const std::string&);
std::string Basename(const std::string&);
std::string Dirname(const std::string&);
bool WriteStringToFd(const std::string&, borrowed_fd);
}
static int check(bool ok,const char* label) { printf("%s %s\n",ok?"PASS":"FAIL",label);return ok?0:1; }
int main() {
 using namespace android::base;
 int failed=0;
 failed+=check(Trim(std::string(" \t shim \n"))=="shim","Trim whitespace");
 failed+=check(Trim(std::string()).empty(),"Trim empty");
 failed+=check(Trim(std::string(4096,'x'))==std::string(4096,'x'),"Trim heap string");
 failed+=check(Basename(std::string("/vendor/lib64/example.so"))=="example.so","Basename");
 failed+=check(Dirname(std::string("/vendor/lib64/example.so"))=="/vendor/lib64","Dirname");
 int fd[2];if(pipe(fd))return 2;
 std::string data("shim\0payload",12);
 failed+=check(WriteStringToFd(data,borrowed_fd(fd[1])),"WriteStringToFd result");
 close(fd[1]);char buffer[32]={};ssize_t count=read(fd[0],buffer,sizeof(buffer));close(fd[0]);
 failed+=check(count==static_cast<ssize_t>(data.size())&&!memcmp(buffer,data.data(),data.size()),"WriteStringToFd embedded NUL");
 failed+=check(!WriteStringToFd(std::string("error"),borrowed_fd(-1)),"WriteStringToFd invalid fd");
 const char* symbols[]={
 "_ZN7android4base4TrimERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEE",
 "_ZN7android4base8BasenameERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEE",
 "_ZN7android4base7DirnameERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEE",
 "_ZN7android4base15WriteStringToFdERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEENS0_11borrowed_fdE"};
 for(auto name:symbols){Dl_info info={};void* fn=dlsym(RTLD_DEFAULT,name);bool ok=fn&&dladdr(fn,&info)&&strstr(info.dli_fname,"/vendor/")&&strstr(info.dli_fname,"/libbase_shim.so");printf("OWNER %s %s\n",name,fn?info.dli_fname:"MISSING");failed+=check(ok,"old ABI provider");}
 return failed?1:0;
}
