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
        self.function_a()

    def function_e(self):
        self.logger.trace("Function E called")
        self.function_d()

    def function_f(self):
        self.logger.warning("Function F called")
        self.function_b()

    def function_g(self):
        self.logger.error("Function G called")
        self.function_f()

if __name__ == "__main__":
    cls = TestClass()
    cls.logger.header("Test")
    cls.function_a()
    cls.function_b()
    cls.function_c()
    cls.function_d()
    cls.function_e()
    cls.function_f()
    cls.function_g()