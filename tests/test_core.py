# -*- coding: utf-8 -*-

from .data import target_program
import platform
import subprocess
import sys
import threading
try:
    import unittest2 as unittest
except:
    import unittest

import frida


class TestCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        system = platform.system()
        cls.target = subprocess.Popen([target_program], stdin=subprocess.PIPE)
        cls.session = frida.attach(cls.target.pid)

    @classmethod
    def tearDownClass(cls):
        cls.session.detach()
        cls.target.terminate()
        cls.target.stdin.close()

    def test_enumerate_devices(self):
        devices = frida.get_device_manager().enumerate_devices()
        self.assertTrue(len(devices) > 0)

    def test_enumerate_modules(self):
        modules = self.session.enumerate_modules()
        self.assertGreater(len(modules), 1)
        m = modules[0]
        self.assertIsInstance(repr(m), str)
        self.assertIsInstance(str(m), str)

    def test_enumerate_ranges(self):
        ranges = self.session.enumerate_ranges('r--')
        self.assertTrue(len(ranges) > 0)
        r = ranges[0]
        self.assertIsInstance(repr(r), str)
        self.assertIsInstance(str(r), str)

    def test_find_base_address(self):
        m = self.session.enumerate_modules()[0]
        self.assertEqual(self.session.find_base_address(m.name), m.base_address)
        self.assertEqual(self.session.find_base_address(m.name + "_does_not_exist$#@$"), 0)

    def test_memory_access(self):
        result = {}
        event = threading.Event()
        def on_message(message, data):
            self.assertEqual(message['type'], 'send')
            result['address'] = int(message['payload'], 16)
            event.set()

        script = self.session.create_script(name="test-memory-access", source="""\
hello = Memory.allocUtf8String("Hello");
send(hello);
""")
        script.on('message', on_message)
        script.load()
        event.wait()
        hello_address = result['address']

        self.assertListEqual([x for x in iterbytes(self.session.read_bytes(hello_address, 6))],
            [0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x00])
        self.assertEqual(self.session.read_utf8(hello_address), "Hello")

        self.session.write_bytes(hello_address, b"Yo\x00")
        self.assertListEqual([x for x in iterbytes(self.session.read_bytes(hello_address, 6))],
            [0x59, 0x6f, 0x00, 0x6c, 0x6f, 0x00])
        self.assertEqual(self.session.read_utf8(hello_address), "Yo")
        self.session.write_utf8(hello_address, "Hei")
        self.assertListEqual([x for x in iterbytes(self.session.read_bytes(hello_address, 6))],
            [0x48, 0x65, 0x69, 0x00, 0x6f, 0x00])
        self.assertEqual(self.session.read_utf8(hello_address), "Hei")

        script.off('message', on_message)
        script.unload()

    def test_enumerate_module_exports(self):
        m = self.session.enumerate_modules()[1]
        exports = m.enumerate_exports()
        e = exports[0]
        self.assertIsInstance(repr(e), str)
        self.assertIsInstance(str(e), str)

    def test_enumerate_module_ranges(self):
        m = self.session.enumerate_modules()[1]
        ranges = m.enumerate_ranges('r--')
        r = ranges[0]
        self.assertIsInstance(repr(r), str)
        self.assertIsInstance(str(r), str)

if sys.version_info[0] >= 3:
    iterbytes = lambda x: iter(x)
else:
    def iterbytes(data):
        return (ord(char) for char in data)


if __name__ == '__main__':
    unittest.main()
