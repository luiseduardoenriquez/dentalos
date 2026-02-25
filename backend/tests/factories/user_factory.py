import factory
from faker import Faker

fake = Faker("es_CO")


class UserFactory(factory.Factory):
    class Meta:
        model = dict

    email = factory.LazyFunction(lambda: fake.email())
    password = "TestPass1"
    name = factory.LazyFunction(lambda: fake.name())
    role = "doctor"
    phone = factory.LazyFunction(lambda: f"+57{fake.msisdn()[:10]}")
