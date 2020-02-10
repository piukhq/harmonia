from marshmallow.fields import DateTime
import pendulum


class PendulumField(DateTime):
    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        return pendulum.instance(value)
