# Copyright (C) 2023-2025 The LineageOS Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ifdef MANIFEST_EXCLUDES
MANIFEST_EXCLUDES := |$(MANIFEST_EXCLUDES)
endif

# 本地改动：.repo 目录已删除（为释放磁盘空间），repo 工具不可用。
# 有 .repo/repo/repo 时行为与上游一致；否则写一个占位 manifest，
# 该文件仅记录源码来源，不影响系统功能。
$(INSTALLED_BUILD_MANIFEST_XML_TARGET):
	mkdir -p $(dir $@)
	if [ -f .repo/repo/repo ]; then \
	    python3 .repo/repo/repo manifest -o - -r | grep -Ev "proprietary_$(MANIFEST_EXCLUDES)" > $@ ; \
	else \
	    echo '<?xml version="1.0" encoding="UTF-8"?>' > $@ ; \
	    echo '<!-- .repo removed: build manifest unavailable, source revisions not recorded -->' >> $@ ; \
	    echo '<manifest></manifest>' >> $@ ; \
	fi

.PHONY: build-manifest.xml
build-manifest.xml: $(INSTALLED_BUILD_MANIFEST_XML_TARGET)
