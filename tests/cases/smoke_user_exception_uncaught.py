class ValidationError(ValueError):
    def __init__(self, field):
        super().__init__("bad field: %s" % field)
        self.field = field


raise ValidationError("name")
