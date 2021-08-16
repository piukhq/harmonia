import pendulum
from marshmallow.fields import DateTime


class PendulumField(DateTime):
    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        return pendulum.instance(value)
