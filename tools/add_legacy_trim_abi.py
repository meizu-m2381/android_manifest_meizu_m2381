"""Keep the vendor libbase ABI used by m2381's API 33 HALs.

Export the original non-template Trim signature alongside today's template
instantiations, plus old string signatures for WriteStringToFd and Basename.
Restrict these compatibility entries to the vendor variant.
"""

import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aosp", type=Path)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    path = args.aosp / "system/libbase/strings.cpp"
    original = path.read_text()
    marker = "// m2381 API 33 vendor ABI compatibility."
    anchor = "template std::string Trim(std::string_view&&);\n"
    assert original.count(anchor) == 1
    addition = """
#if defined(__ANDROID_VENDOR__)
// m2381 API 33 vendor ABI compatibility.
// Stock health, boot-control and NFC HALs reference the old non-template symbol.
std::string Trim(const std::string& s) {
  return Trim<const std::string&>(s);
}
#endif
"""
    args.backup.mkdir(parents=True, exist_ok=True)
    if marker not in original:
        saved = args.backup / "strings.cpp"
        if not saved.exists():
            shutil.copy2(path, saved)
        path.write_text(original.replace(anchor, anchor + addition))
        print("updated", path)
    path = args.aosp / "system/libbase/file.cpp"
    original = path.read_text()
    marker = "// m2381 API 33 file ABI compatibility."
    if marker in original:
        return
    anchor = "static bool CleanUpAfterFailedWrite(const std::string& path) {"
    assert original.count(anchor) == 1
    addition = """#if defined(__ANDROID_VENDOR__)
// m2381 API 33 file ABI compatibility.
bool WriteStringToFd(const std::string& content, borrowed_fd fd) {
  return WriteStringToFd(std::string_view(content), fd);
}

std::string Basename(const std::string& path) {
  return Basename(std::string_view(path));
}
#endif

"""
    saved = args.backup / "file.cpp"
    if not saved.exists():
        shutil.copy2(path, saved)
    path.write_text(original.replace(anchor, addition + anchor))
    print("updated", path)


if __name__ == "__main__":
    main()
