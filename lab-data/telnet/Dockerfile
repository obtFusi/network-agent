FROM alpine:3.21
RUN apk add --no-cache busybox-extras \
    && echo 'root:telnet123' | chpasswd
CMD ["/usr/sbin/telnetd", "-F", "-l", "/bin/sh", "-b", "0.0.0.0:23"]
