from time import sleep

from smdb_logger import Logger, LEVEL

class TestClass:
    logger = Logger(log_to_console=True, level=LEVEL.TRACE, use_caller_name=True, use_file_names=True)

    def function_a(self):
        self.logger.info("Function A called")

    def function_b(self):
        self.logger.info("Function B called")

    def function_c(self):
        self.logger.info("Function C called")

    def function_d(self):
        self.logger.debug("Function D called")
        sleep(0.1)
        self.function_a()

    def function_e(self):
        self.logger.trace("Function E called")
        sleep(0.1)
        self.function_d()

    def function_f(self):
        self.logger.warning("Function F called")
        sleep(0.1)
        self.function_b()

    def function_g(self):
        self.logger.error("Function G called")
        sleep(0.1)
        self.function_f()

    def function_h(self):
        self.logger.heartbeat("Function H called")

if __name__ == "__main__":
    cls = TestClass()
    cls.logger.header("Test")
    sleep(0.1)
    cls.function_a()
    sleep(0.1)
    cls.function_b()
    sleep(0.1)
    cls.function_c()
    sleep(0.1)
    cls.function_d()
    sleep(0.1)
    cls.function_e()
    sleep(0.1)
    cls.function_f()
    sleep(0.1)
    cls.function_g()
    sleep(0.1)
    cls.function_h()