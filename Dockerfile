FROM python:3.9-slim

RUN echo "deb http://deb.debian.org/debian bookworm main non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian-security bookworm-security main non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian bookworm-updates main non-free non-free-firmware" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y \
    wireless-tools \
    wpasupplicant \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    usbutils \
    wireless-tools \
    iw \
    wpasupplicant \
    net-tools \
    firmware-linux-nonfree \
    firmware-misc-nonfree

RUN mkdir -p /lib/firmware/mt7601u && \
    wget https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/mediatek/mt7601u.bin -O /lib/firmware/mt7601u/mt7601u.bin || \
    wget https://github.com/OpenELEC/mt7601u-firmware/raw/master/mt7601u.bin -O /lib/firmware/mt7601u/mt7601u.bin

RUN apt-get purge -y wget ca-certificates && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/logs

CMD ["python", "src/main.py"]
