import subprocess
import time
import sys
import select
import fcntl
import os
import re

def set_non_blocking(file_descriptor):
    flags = fcntl.fcntl(file_descriptor, fcntl.F_GETFL)
    fcntl.fcntl(file_descriptor, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def safe_decode(byte_string):
    try:
        return byte_string.decode('utf-8')
    except UnicodeDecodeError:
        return byte_string.decode('latin-1')

def run_qemu_test():
    cmd = "~/pro/qemu/build/qemu-system-x86_64 -hda ~/pro/images/disk.img -smp cpus=32 -nographic"
    process = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    set_non_blocking(process.stdout.fileno())
    set_non_blocking(process.stderr.fileno())

    timeout = 60
    start_time = time.time()

    boot_success = False
    qemu_terminated = False
    output_buffer = ""
    output_lines = []

    while time.time() - start_time < timeout:
        reads = [process.stdout, process.stderr]
        ret = select.select(reads, [], [], 0.1)

        for fd in ret[0]:
            try:
                chunk = fd.read(1024)
                if chunk:
                    decoded_chunk = safe_decode(chunk)
                    output_buffer += decoded_chunk
                    lines = output_buffer.splitlines(True)
                    output_buffer = ""
                    for line in lines:
                        if line.endswith('\n'):
                            output_lines.append(line.strip())
                            print(line.strip())
                            if re.search(r"Boot took \d+(\.\d+)? seconds", line):
                                boot_success = True
                        else:
                            output_buffer += line
            except (IOError, OSError):
                pass

        if boot_success:
            break

    if boot_success:
        process.stdin.write(b"\x01")
        process.stdin.write(b"x")
        process.stdin.flush()

        while time.time() - start_time < timeout:
            if process.poll() is not None:
                qemu_terminated = True
                break

    process.terminate()

    if boot_success and qemu_terminated:
        return True, "Test successful: Boot success and exit normally", '\n'.join(output_lines)
    elif boot_success and not qemu_terminated:
        return False, "Test failed: Boot success but QEMU terminated", '\n'.join(output_lines)
    else:
        return False, "Test failed: Boot failed", '\n'.join(output_lines)

def main():
    max_tests = 100
    for i in range(1, max_tests + 1):
        print(f"Start testing {i}")
        success, result, output = run_qemu_test()
        print(result)

        if not success:
            print("Test failed, QEMU output:")
            print(output)
            print(f"Test failed at {i}，stop")
            return

        print("------------------------")

    print(f"Completed {max_tests} tests，all successful")

if __name__ == "__main__":
    main()
