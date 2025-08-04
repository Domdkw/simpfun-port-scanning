# MIT License ,See https://github.com/Domdkw/simpfun-port-scanning/blob/master/LICENSE
from mcstatus import JavaServer
import csv
import os
import concurrent.futures
from queue import Queue
import threading
import time
import platform

# 配置参数
SERVER_ADDRESS = "play.simpfun.cn"
start_port_input = input("请输入起始端口[10000]: ").strip()
START_PORT = int(start_port_input) if start_port_input else 10000
print(f"起始端口: {START_PORT}")
end_port_input = input("请输入结束端口[65533]: ").strip()
END_PORT = int(end_port_input) if end_port_input else 65533
print(f"结束端口: {END_PORT}")
THREAD_COUNT = 10
CSV_FILENAME = "simpfun_server_scan_results.csv"

# 新增配置参数
DEFAULT_PORT_DELAY = 1  # 默认端口扫描后等待时间(秒)
BATCH_DELAY = 1  # 每批扫描完成后等待时间(秒)

# 计算总端口数
total_ports = END_PORT - START_PORT + 1

# 存储活跃服务器列表
active_servers = []

# 存储扫描结果的队列和列表
result_queue = Queue()
scan_results = []

# 控制CSV文件是否已创建
csv_file_created = False
csv_lock = threading.Lock()

def get_minecraft_server_status(server_address, server_port):
    """
    获取Minecraft服务器状态
    :param server_address: 服务器地址
    :param server_port: 服务器端口
    :return: 服务器状态字典或None
    """
    try:
        server = JavaServer(server_address, server_port)
        status = server.status()

        # 提取相关信息
        online_count = status.players.online
        max_players = status.players.max
        version = status.version.name
        protocol = status.version.protocol
        latency = status.latency

        result = {
            "server_address": server_address,
            "server_port": server_port,
            "online_count": online_count,
            "max_players": max_players,
            "version": version,
            "protocol": protocol,
            "latency": latency
        }
        # 只将成功响应的服务器添加到结果队列
        result_queue.put(result)
        return result
    except Exception as e:
        # 记录未响应的服务器，但不添加到结果队列
        print(f"服务器 {server_address}:{server_port} 未响应: {e}")
        return None


def write_results_to_csv():
    """
    将扫描结果写入CSV文件
    第一次运行时创建文件并写入表头，后续运行时追加内容
    """
    global csv_file_created

    with csv_lock:
        # 检查是否是第一次创建文件
        file_exists = os.path.exists(CSV_FILENAME)
        mode = 'a' if (file_exists and csv_file_created) else 'w'

        with open(CSV_FILENAME, mode, newline='', encoding='utf-8') as csvfile:
            fieldnames = ['server_address', 'server_port', 'online_count', 'max_players', 'version', 'protocol', 'latency']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # 如果是第一次创建文件，写入表头
            if mode == 'w':
                writer.writeheader()
                csv_file_created = True
                if file_exists:
                    print(f"已删除旧的结果文件并创建新文件: {CSV_FILENAME}")
                else:
                    print(f"已创建结果文件: {CSV_FILENAME}")

            # 只写入成功响应的服务器结果
            while not result_queue.empty():
                result = result_queue.get()
                # 确保只写入version不是N/A的服务器
                if result['version'] != 'N/A':
                    writer.writerow(result)
                    scan_results.append(result)

        print(f"扫描结果已更新到: {CSV_FILENAME}")


def clear_screen():
    """清空控制台屏幕"""
    # 根据操作系统执行不同的清屏命令
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

def clear_upper_screen():
    """只清空屏幕上方内容，保留底部进度条"""
    try:
        import shutil
        terminal_height = shutil.get_terminal_size().lines
        # 移动光标到顶部
        print('\033[H', end='')
        # 清除从顶部到进度条上方的所有内容
        print('\033[{};1H\033[J'.format(terminal_height - 1), end='')
    except:
        # 如果无法获取终端高度，使用简单方法
        print('\033[H\033[J', end='')

def update_progress(progress, total):
    """
    更新并显示进度条在屏幕底部
    :param progress: 当前进度
    :param total: 总进度
    """
    # 获取终端高度
    try:
        import shutil
        terminal_height = shutil.get_terminal_size().lines
        # 移动光标到屏幕底部行的开头
        print('\033[{};0H'.format(terminal_height), end='')
        # 清除当前行
        print('\033[K', end='')
    except:
        # 如果无法获取终端高度，使用固定行数
        print('\n' * 20, end='')

    percent = (progress / total) * 100
    bar_length = 50
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'进度: |{bar}| {percent:.1f}% ({progress}/{total})', end='')
    # 保持在底部，不移动光标

def print_server_info(servers):
    """
    在屏幕上方打印服务器信息
    :param servers: 服务器列表
    """
    try:
        import shutil
        terminal_height = shutil.get_terminal_size().lines
        # 移动光标到顶部
        print('\033[H', end='')
    except:
        pass

    if servers:
        print("发现活跃服务器:")
        for server in servers:
            print(f"服务器 {server['server_address']}:{server['server_port']} - 在线人数: {server['online_count']}/{server['max_players']}, 版本: {server['version']}")
    else:
        print("当前批次未发现活跃服务器")


def scan_port(port):
    """
    扫描指定端口
    :param port: 端口号
    """
    global scanned_count
    status = get_minecraft_server_status(SERVER_ADDRESS, port)
    scanned_count += 1
    if status is not None and status['online_count'] != 'N/A':
        active_servers.append(status)


if __name__ == "__main__":
    # 检查并初始化CSV文件
    if os.path.exists(CSV_FILENAME):
        os.remove(CSV_FILENAME)
        print(f"已删除旧的结果文件: {CSV_FILENAME}")
    csv_file_created = False

    # 获取用户输入
    # 1. 获取服务器状态的等待时间
    try:
        delay_input = input(f"请输入获取服务器状态的等待时间(秒) [{DEFAULT_PORT_DELAY}]: ").strip()
        if delay_input == '':
            port_delay = DEFAULT_PORT_DELAY
        else:
            port_delay = float(delay_input)
        print(f"设置等待时间为: {port_delay} 秒")
    except ValueError:
        print(f"输入无效，使用默认等待时间: {DEFAULT_PORT_DELAY} 秒")
        port_delay = DEFAULT_PORT_DELAY

    # 获取扫描线程数（同时用作批次大小）
    try:
        thread_input = input(f"请输入扫描线程数 [{THREAD_COUNT}]: ").strip()
        if thread_input == '':
            thread_count = THREAD_COUNT
        else:
            thread_count = int(thread_input)
            if thread_count <= 0:
                raise ValueError
        # 设置批次大小等于线程数
        BATCH_SIZE = thread_count
        print(f"设置线程数和批次大小均为: {thread_count}")
    except ValueError:
        print(f"输入无效，使用默认线程数和批次大小: {THREAD_COUNT}")
        thread_count = THREAD_COUNT
        BATCH_SIZE = THREAD_COUNT

    # 使用用户设置的等待时间更新配置
    BATCH_DELAY = port_delay

    # 清空屏幕
    clear_screen()

    # 初始化扫描计数
    global scanned_count
    scanned_count = 0

    # 使用线程池进行多线程扫描
    print(f"开始使用 {thread_count} 个线程扫描端口 {START_PORT}-{END_PORT}...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        # 分批次提交端口扫描任务
        for i in range(START_PORT, END_PORT + 1, BATCH_SIZE):
            batch_end = min(i + BATCH_SIZE - 1, END_PORT)
            batch_ports = range(i, batch_end + 1)

            # 提交当前批次的任务
            futures = [executor.submit(scan_port, port) for port in batch_ports]

            # 等待当前批次完成
            concurrent.futures.wait(futures)

            # 处理结果
            write_results_to_csv()

            # 显示活跃服务器信息
            print_server_info(active_servers[-BATCH_SIZE:])  # 只显示当前批次的活跃服务器

            # 这段代码移动到等待之后执行
            if i + BATCH_SIZE <= END_PORT:
                clear_upper_screen()
                active_servers.clear()  # 清空当前批次的活跃服务器列表

            print(f"----------------------------------------------")
            print(f"当前批次: {i}-{batch_end}")
            print(f"----------------------------------------------")
            # 显示进度
            update_progress(scanned_count, total_ports)

            # 不是最后一批次则等待
            if i + BATCH_SIZE <= END_PORT:
                try:
                    import shutil
                    terminal_height = shutil.get_terminal_size().lines
                    # 移动光标到进度条上方
                    print('\033[{};0H'.format(terminal_height - 1), end='')
                    # 清除当前行
                    print('\033[K', end='')
                    print(f"等待 {BATCH_DELAY} 秒后继续...")
                except:
                    print(f"\n等待 {BATCH_DELAY} 秒后继续...")
                time.sleep(BATCH_DELAY)
                clear_upper_screen()
                active_servers.clear()  # 清空当前批次的活跃服务器列表

    # 扫描完成后显示总结
    clear_screen()
    print("所有端口扫描完成!")
    print(f"总共扫描了 {total_ports} 个端口，发现 {len(active_servers)} 个活跃服务器。")
    print(f"扫描结果已保存到: {CSV_FILENAME}")