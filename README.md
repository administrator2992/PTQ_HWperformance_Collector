# PTQ HW Performance Collector

Collecting Latency, Memory RSS, PSS, USS, and CPU as well as the power comsumption while post-quantization deep learning infer the input. GPU is included for Jetson Devices
(Still in Dev Mode)

## DL Application Properties

Flower classification. Trained from Oxford Flower 102 dataset.

## DL models Zoo

Recently, provided the DL model in TFLite and TensorRT format

* [Link Example PTQ DL Models](https://drive.google.com/drive/folders/1R9VFMJfhEo8WbOKl4ZeI_5ZNmLiZ965q?usp=sharing)

## Pre-requirements

Install measurement application

```shell
sudo apt-get update

# sysstat
sudo apt install sysstat

# cgroup-tools
sudo apt install cgroup-tools

# depedencies
sudo pip install -r requirements_<device_label/>.txt

# install tensorrt on Jetson Nano
sudo apt install tensorrt

# install tensorflow for Jetson Nano
sudo ./install_protobuf-3.14.0.sh
sudo apt-get install -y python3-pip pkg-config
sudo apt-get install -y libhdf5-serial-dev hdf5-tools libhdf5-dev zlib1g-dev zip libjpeg8-dev liblapack-dev libblas-dev gfortran
sudo ln -s /usr/include/locale.h /usr/include/xlocale.h
sudo pip3 install --verbose 'Cython<3'
sudo wget --no-check-certificate https://developer.download.nvidia.com/compute/redist/jp/v461/tensorflow/tensorflow-2.7.0+nv22.1-cp36-cp36m-linux_aarch64.whl
sudo pip3 install --verbose tensorflow-2.7.0+nv22.1-cp36-cp36m-linux_aarch64.whl
```

Active the cgroup control
```shell
# for raspberry pi, add command in /boot/cmdline.txt
systemd.unified_cgroup_hierarchy=0 cgroup_enable=memory cgroup_memory=1 swapaccount=1

sudo cgcreate -g memory:<cgroup_name>
sudo su -c 'echo <stop_scenario>M > /sys/fs/cgroup/memory/<cgroup_name>/memory.limit_in_bytes'
sudo su -c 'echo 10 > /sys/fs/cgroup/memory/<cgroup_name>/memory.swappiness'
sudo su -c 'echo <stop_scenario>M > /sys/fs/cgroup/memory/<cgroup_name>/memory.memsw.limit_in_bytes'
```

## How it works ?
Call `run_scenario.py` with these parameters by root

Tips : run the program with `nohup` and background job (`&`). Log save in `run_scenario_<device_type>.log` automatically generate.

```
usage: run_scenario.py [-h] --model_path MODEL_PATH --dev_type DEV_TYPE [--threads THREADS] --iterations ITERATIONS --cgroup_name
                       CGROUP_NAME

optional arguments:
  -h, --help            show this help message and exit
  --model_path MODEL_PATH
                        Path of the model
  --dev_type DEV_TYPE   device type | see in yaml file list
  --threads THREADS     num_threads (just for tflite)
  --iterations ITERATIONS
                        how many model runs (not including warm-up)
  --cgroup_name CGROUP_NAME
                        cgroup name named in cgroup settings
```

Save password in `._config.ini` for the example

```._config.ini
[Credentials]
password = your_secure_password
```

After clone, make sure the owner folder level is 700 and for ini file is 600

```bash
chmod 700 DLperformance_Collector
chmod 600 ._config.ini
```

if the process is suddenly stopped, call `fg` to insert your password and `ctrl+z`, and then call `bg` for running the process on the background

## Test the benchmark ?
Call `dlpref_meter/benchmark.py` in `main` folder by root

```
usage: benchmark.py [-h] --model MODEL --type TYPE [--threads THREADS] [--iterations ITERATIONS]

optional arguments:
  -h, --help            show this help message and exit
  --model MODEL         Path of the detection model
  --type TYPE           device types
  --threads THREADS     num_threads (just for tflite)
  --iterations ITERATIONS
                        how many model runs (auto add warmup once)
```
