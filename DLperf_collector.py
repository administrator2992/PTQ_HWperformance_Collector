import os
import gc
import subprocess
import threading
import time
import psutil
import tensorflow as tf
import tensorflow_datasets as tfds
import numpy as np
import pandas as pd
from silence_tensorflow import silence_tensorflow

silence_tensorflow()

class CPU(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.result = None
        self.event = threading.Event()
        self._list = []

    def run(self):
        try:
            while not self.event.is_set():
                output = subprocess.check_output(['pidstat', '-p', str(os.getpid()), '1', '1'])
                cpu_ = float(output.splitlines()[-2].split()[-3])
                if cpu_ > 0.0:
                    with threading.Lock():
                        self._list.append(cpu_)
            self.event.clear()
            res = sum(self._list) / len(self._list)
            self.result = res, self._list
        except Exception as e:
            print(f"Error in CPU measurement : {e}")
            self.result = 0, self._list

    def stop(self):
        self.event.set()

def rss_memory():
    process = psutil.Process()
    mem_info = process.memory_info()
    return mem_info.rss

def get_size(file_path, unit='MB'):
    file_size = os.path.getsize(file_path)
    exponents_map = {'Bytes': 0, 'KB': 1, 'MB': 2, 'GB': 3}
    if unit not in exponents_map:
        raise ValueError("Must select from ['Bytes', 'KB', 'MB', 'GB']")
    else:
        size = file_size / (1024 ** exponents_map[unit])
        return round(size, 2)

def evaluate(model_dir: str, max_batch_size, batch_size_step):
    list_model = os.listdir(model_dir)

    test_set = tfds.load(
            name='oxford_flowers102',
            split='test[:20%]',
            with_info=False,
            as_supervised=True
        )

    for model_name in list_model:
        print("Model Name:", model_name)

        if 'MobileNetV3' in model_name:
            from keras.applications.mobilenet_v3 import preprocess_input
        elif 'EfficientNet' in model_name:
            from keras.applications.efficientnet import preprocess_input
        elif 'DenseNet' in model_name:
            from keras.applications.densenet import preprocess_input

        def resize_image(image, label):
            image = tf.image.resize(image, size=(224, 224))
            image = tf.cast(image, dtype=tf.float32)
            image = preprocess_input(image)
            return image, label

        test_set = test_set.map(map_func=resize_image, num_parallel_calls=tf.data.AUTOTUNE)

        for BATCH_SIZE in np.arange(0, max_batch_size + batch_size_step, batch_size_step):
            if BATCH_SIZE == 0:
                BATCH_SIZE = 1
            print("Batch Size:", BATCH_SIZE)
            data = {'Model': [], 'Model Size (MB)': [], 'Dataset':['oxford_flowers102'],
            'Num. of Test Imgs':[len(test_set)], 'Batch Size': [],
            'Accuracy (%)': [], 'Latency (ms)': [], 'CPU Usage (%)': [],
            'Memory Usage (MB)': []}
            data['Batch Size'].append(BATCH_SIZE)
            data['Model'].append(model_name)
            test_set_batched = test_set.batch(batch_size=BATCH_SIZE)

            model_path = os.path.join(model_dir, model_name)
            data['Model Size (MB)'].append(get_size(model_path, 'MB'))

            interpreter = tf.lite.Interpreter(model_path=model_path)
            interpreter.allocate_tensors()

            input_details = interpreter.get_input_details()[0]
            output_details = interpreter.get_output_details()[0]

            predicted_labels = []
            true_labels = []

            perf = {'Latency (ms)': [], 'CPU Usage (%)': [],
            'Memory Usage (MB)': []}

            for image_batch, label_batch in test_set_batched:
                for index in range(len(label_batch)):
                    true_labels.append(label_batch[index].numpy())
                
                thread = CPU()
                thread.start()
                time.sleep(2)
                start = time.time()

                for image in image_batch:
                    if input_details['dtype'] == np.uint8:
                        input_scale, input_zero_point = input_details["quantization"]
                        image = image / input_scale + input_zero_point

                    image = np.expand_dims(image, axis=0).astype(input_details["dtype"])
                    interpreter.set_tensor(input_details["index"], image)
                    interpreter.invoke()
                    output = interpreter.get_tensor(output_details["index"])[0]
                    prediction = output.argmax()
                    predicted_labels.append(prediction)

                elapsed = (time.time() - start) * 1000
                perf['Latency (ms)'].append(elapsed)
                perf['Memory Usage (MB)'].append(rss_memory())
                if elapsed < 1000:
                    time.sleep((2000-elapsed)/1000)
                thread.stop()
                thread.join()
                perf['CPU Usage (%)'].append(float(thread.result[0]))
                # clear cache
                os.system(f"echo {args.passwd} | sudo -S sync; sudo -S su -c 'echo 3 > /proc/sys/vm/drop_caches'")
                gc.collect()
            
            data['Latency (ms)'].append(round(sum(perf['Latency (ms)'])/len(perf['Latency (ms)']), 2))
            data['Memory Usage (MB)'].append(round((sum(perf['Memory Usage (MB)'])/len(perf['Memory Usage (MB)']))/1024**2, 2))
            data['CPU Usage (%)'].append(round(sum(perf['CPU Usage (%)'])/len(perf['CPU Usage (%)']), 2))

            accurate_count = np.sum(np.array(predicted_labels) == np.array(true_labels))
            data['Accuracy (%)'].append(round(accurate_count * 100.0 / len(predicted_labels), 2))

            print("*" * 25)

            df = pd.DataFrame(data)
            output_path = 'DLperformance_list.csv'
            if os.path.exists(output_path):
                df.to_csv(output_path, mode='a', header=False)
            else:
                df.to_csv(output_path)

        print('='*25)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--model_dir', help='Path of the model directory', required=True)
    parser.add_argument('--max_batch_size', help="maximum batch zise in looping", default=32)
    parser.add_argument('--batch_size_step', help='looping step in batch size fluctuation', default=8)
    args = parser.parse_args()

    st = time.time()
    worker = evaluate(args.model_dir, int(args.max_batch_size), int(args.batch_size_step))
    print(f"DLperformance Collector has measured in {time.time() - st} seconds")
