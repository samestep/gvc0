# Use an appropriate base image
FROM --platform=linux/amd64 ubuntu:20.04

# Set DEBIAN_FRONTEND to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary tools
RUN apt-get update && apt-get upgrade -y && apt-get install -y git wget build-essential python3 python3-pip python-is-python3

# Install sbt (Scala Build Tool)
RUN apt-get update
RUN apt-get install apt-transport-https curl gnupg -yqq
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | tee /etc/apt/sources.list.d/sbt_old.list
RUN curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/scalasbt-release.gpg --import
RUN chmod 644 /etc/apt/trusted.gpg.d/scalasbt-release.gpg
RUN apt-get update
RUN apt-get install sbt

# Install Java (OpenJDK 17)
RUN apt-get install -y openjdk-17-jdk

# Set default JVM memory settings (adjust as needed)
ENV JAVA_OPTS="-Xms2g -Xmx20g"

# Check available versions of the dependencies
RUN apt-cache policy build-essential libgmp10 libpng16-16

# Clone Z3 and build it
RUN git clone https://github.com/Z3Prover/z3.git && \
    cd z3 && \
    python3 scripts/mk_make.py --prefix=/usr && \
    cd build && \
    make && make install

# Set Z3_PATH environment variable
ENV Z3_PATH /usr/bin/z3

# Clone the Silver and Silicon repositories
RUN git clone https://github.com/gradual-verification/silver-gv.git && \
    git clone https://github.com/gradual-verification/silicon-gv.git

# Create symlinks
RUN cd silicon-gv && ln -s ../silver-gv silver

# Clone gvc0 and create symlink to silicon
RUN git clone https://github.com/gradual-verification/gvc0 && \
    cd gvc0 && ln -s ../silicon-gv silicon

# Install the specific dependencies for cc0
RUN apt-get install -y build-essential libgmp10 libpng16-16

# Install cc0
RUN wget https://c0.cs.cmu.edu/downloads/cc0-debian.deb
RUN apt install ./cc0-debian.deb

# Set the working directory
WORKDIR /gvc0

# Command to keep the container running
CMD ["tail", "-f", "/dev/null"]
