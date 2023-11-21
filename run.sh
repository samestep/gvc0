#!/usr/bin/env bash
java -Xss30M -Xmx12G -jar target/scala-2.12/gvc0-assembly-0.1.0-SNAPSHOT.jar "$@"
