#!/bin/bash
set -euxo pipefail

clang -v && ld.lld -v

sed -i 's/-dirty//g' scripts/setlocalversion

#export KBUILD_BUILD_USER=$USER
#export KBUILD_BUILD_HOST=$HOST
export KMI_GENERATION=9
export BRANCH='android12-5.10' || exit 1

scripts/setlocalversion --save-scmversion . $BRANCH $KMI_GENERATION || exit 1 
make -j5 V=0 LLVM=1 LLVM_IAS=1 O=out gki_defconfig CROSS_COMPILE=aarch64-linux-gnu-
cat out/.config
make -j5 V=0 LLVM=1 LLVM_IAS=1 O=out CROSS_COMPILE=aarch64-linux-gnu-

cp out/Module.symvers kmi/module.symvers

cd kmi
python3 kmi.py
cd ..

AOSP_MIRROR=https://android.googlesource.com
BRANCH=main-kernel-build-2024
git clone $AOSP_MIRROR/platform/prebuilts/build-tools -b $BRANCH --depth 1 build-tools
git clone $AOSP_MIRROR/kernel/prebuilts/build-tools -b $BRANCH --depth 1 kernel-build-tools
git clone $AOSP_MIRROR/platform/system/tools/mkbootimg -b $BRANCH --depth 1
export AVBTOOL=./kernel-build-tools/linux-x86/bin/avbtool
export GZIP=./build-tools/path/linux-x86/gzip
export LZ4=./build-tools/path/linux-x86/lz4
export MKBOOTIMG=./mkbootimg/mkbootimg.py
export UNPACK_BOOTIMG=./mkbootimg/unpack_bootimg.py
GKI_URL=https://dl.google.com/android/gki/gki-certified-boot-android12-5.10-2024-05_r1.zip
status=$(curl -sL -w "%{http_code}" "$GKI_URL" -o /dev/null)
if [ "$status" = "200" ]; then
 curl -Lo gki-kernel.zip "$GKI_URL"
else
 exit 1
fi

rm -rf out/kernel 
unzip gki-kernel.zip && rm gki-kernel.zip
echo '[+] Unpack prebuilt boot.img'
BOOT_IMG=$(find . -maxdepth 1 -name "boot*.img")
$UNPACK_BOOTIMG --boot_img="$BOOT_IMG"
rm "$BOOT_IMG"
echo '[+] Building boot.img'
$MKBOOTIMG --header_version 4 --kernel out/arch/arm64/boot/Image.gz --output boot.img --ramdisk out/ramdisk --os_version 12.0.0 --os_patch_level 2023-08
$AVBTOOL add_hash_footer --partition_name boot --partition_size $((64 * 1024 * 1024)) --image boot.img --algorithm SHA256_RSA2048 --key ./kernel-build-tools/linux-x86/share/avb/testkey_rsa2048.pem

