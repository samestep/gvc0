#!/usr/bin/env bash
clang -fpic -O3 -fbracket-depth=1024 -std=c99 -g -fwrapv -Wall -Wextra -pg -emit-llvm -c -I /usr/share/cc0/include -I /usr/share/cc0/runtime -o stress/before_$1.bc stress/recreated_$1.verified.c0.c

llvm-dis -o stress/before_$1.ll stress/before_$1.bc

clang -fpic -O3 -pg -o stress/before_$1 stress/before_$1.bc cc0main.bc -Wl,-rpath,/usr/share/cc0/lib -Wl,-rpath,src/main/resources/ -Wl,-rpath,src/main/resources/ /usr/share/cc0/lib/libconio.so /usr/share/cc0/lib/libargs.so /usr/share/cc0/lib/libstring.so -L /usr/share/cc0/runtime -Wl,-rpath,/usr/share/cc0/runtime /usr/share/cc0/runtime/libc0rt.so

opt -enable-new-pm=0 -load ./DedupDerefs.so -loop-simplify -dedup-derefs stress/before_$1.ll -o stress/after_$1.bc

llvm-dis -o stress/after_$1.ll stress/after_$1.bc

clang -fpic -O3 -pg -o stress/after_$1 stress/after_$1.bc cc0main.bc -Wl,-rpath,/usr/share/cc0/lib -Wl,-rpath,src/main/resources/ -Wl,-rpath,src/main/resources/ /usr/share/cc0/lib/libconio.so /usr/share/cc0/lib/libargs.so /usr/share/cc0/lib/libstring.so -L /usr/share/cc0/runtime -Wl,-rpath,/usr/share/cc0/runtime /usr/share/cc0/runtime/libc0rt.so

