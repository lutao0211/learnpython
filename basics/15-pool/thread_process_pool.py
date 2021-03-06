#!/usr/bin/env python
# encoding: utf-8

import argparse
import concurrent.futures
import random
import os
import multiprocessing as mp
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import jieba
import jieba.posseg as pseg
from loguru import logger


def cut_news_worker(args, file_data):
    """每个线程或进程实际执行的逻辑"""
    label_id, label_name, fname = file_data    
    output_path = os.path.join(args.cut_dir, os.path.basename(fname))
    with open(output_path, "w", encoding="utf-8") as fout:
        line_str = str(label_name) + "\t" + str(label_id) + "\t"
        with open(fname, encoding="utf-8") as fin:
            # 第一行为标题
            line_no = 0
            for line in fin:
                line = line.strip()
                # 跳过空行
                if len(line) == 0:
                    continue

                # 标题
                if line_no == 0:
                    title_str = ""
                    # 存储词和词性
                    words = pseg.cut(line)
                    for word, pos in words:
                        # 跳过空白符
                        if len(word.strip()) == 0:
                            continue
                        title_str += word.strip() + "/" + pos + ","
                    line_str += title_str.rstrip(",") + "\t"

                    line_no += 1
                    continue

                # 正文分词
                content_str = ""
                words = pseg.cut(line)
                for word, pos in words:
                    # 跳过空白符
                    if len(word.strip()) == 0:
                        continue
                    content_str += word.strip() + "/" + pos + ","
                line_str += content_str

        # 存储格式: 标签名 \t 标签id \t 标题分词 \t 正文分词
        fout.write(line_str.rstrip(",") + "\n")

def cut_news_thread_pool(args, label_map):
    """使用线程池对新闻数据集分词"""
    data_list = []
    # 遍历每个类别
    for label_name, label_id in label_map.items():
        data_dir = os.path.join(args.data_dir, label_name)
        # 遍历每个类别目录下的文件，把文件路径全都存储到data_list中
        for root, _, files in os.walk(data_dir):
            for f in files:
                fname = os.path.join(root, f)
                data_list.append((label_id, label_name, fname))
    n_data = len(data_list)
    logger.info("新闻总数为: {}".format(n_data))

    # 随机打乱数据
    random.shuffle(data_list)

    # 线程池的处理方式与之前的多线程处理方式的差异在于
    # 在多线程程序里我们要手动划分数据，然后交由不同线程处理不同数据
    # 而在线程池中数据划分的过程是自动的，只要给定数据和线程数，ThreadPoolExecutor会
    # 自动将数据划分并交给不同的线程处理
    with ThreadPoolExecutor(max_workers=args.n_worker) as e:
        # 异步执行数据处理，返回Future对象，Future对象封装了异步执行的状态和结果
        fs = [e.submit(cut_news_worker, args, file_data) for file_data in data_list]
        # 由于这里cut_news_worker没有返回值，这里未从Future对象获取结果
        # 如果cut_news_worker有返回值的话，则可以通过Future对象来获取结果
        # concurrent.futures.as_completed只处理已经执行完成的Future对象，如果还有
        # 未完成的异步执行则一直会等待异步执行完成
        for _ in concurrent.futures.as_completed(fs):
            # 什么都不做，只是等待所有异步执行结束
            pass

def cut_news_process_pool(args, label_map):
    """使用进程池对新闻数据集分词"""
    data_list = []
    # 遍历每个类别
    for label_name, label_id in label_map.items():
        data_dir = os.path.join(args.data_dir, label_name)
        # 遍历每个类别目录下的文件，把文件路径全都存储到data_list中
        for root, _, files in os.walk(data_dir):
            for f in files:
                fname = os.path.join(root, f)
                data_list.append((label_id, label_name, fname))
    n_data = len(data_list)
    logger.info("新闻总数为: {}".format(n_data))

    # 随机打乱数据
    random.shuffle(data_list)
    # 进程池的处理方式与之前的多进程处理方式的差异在于
    # 在多进程程序里我们要手动划分数据，然后交由不同进程处理不同数据
    # 而在进程池中数据划分的过程是自动的，只要给定数据和进程数，ProcessPoolExecutor会
    # 自动将数据划分并交给不同的进程处理
    with ProcessPoolExecutor(max_workers=args.n_worker) as e:
        # 异步执行数据处理，返回Future对象，Future对象封装了异步执行的状态和结果
        fs = [e.submit(cut_news_worker, args, file_data) for file_data in data_list]
        # 由于这里cut_news_worker没有返回值，这里未从Future对象获取结果
        # 如果cut_news_worker有返回值的话，则可以通过Future对象来获取结果
        # concurrent.futures.as_completed只处理已经执行完成的Future对象，如果还有
        # 未完成的异步执行则一直会等待异步执行完成
        for _ in concurrent.futures.as_completed(fs):
            # 什么都不做，只是等待所有异步执行结束
            pass

def main():
    parser = argparse.ArgumentParser(description="清华大学THUCNEWS新闻预处理")
    parser.add_argument("--data_dir", type=str, default="/da1/dataset/nlp/thucnews/data", help="原始新闻数据根目录")
    parser.add_argument("--cut_dir", type=str, default="/da1/dataset/nlp/thucnews/cut_data", help="分词后输出目录")
    parser.add_argument("--n_worker", type=int, default=8, help="分词使用线程数或进程数")
    args = parser.parse_args()

    # 解压数据之后我们得到的是中文目录，我们需要把对应的中文目录重命名为英文目录，路径名中最好是不要出现中文
    # 这里我们显式为每个类别赋予一个整数类别id
    label_map = {
        "constellation": 0,         # 星座
        "education": 1,             # 教育
        "entertainment": 2,         # 娱乐
        "fashion": 3,               # 时尚
        "finance": 4,               # 财经
        "game": 5,                  # 游戏
        "home": 6,                  # 家居
        "house": 7,                 # 房产
        "lottery": 8,               # 彩票
        "politics": 9,              # 时政
        "society": 10,              # 社会
        "sports": 11,               # 体育
        "stock": 12,                # 股票
        "technology": 13            # 科技
    }

    #cut_news_thread_pool(args, label_map)

    cut_news_process_pool(args, label_map)

if __name__ == "__main__":
    main()
