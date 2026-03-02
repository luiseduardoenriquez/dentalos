import factory
from faker import Faker

fake = Faker("es_CO")


class PatientFactory(factory.Factory):
    class Meta:
        model = dict

    first_name = factory.LazyFunction(lambda: fake.first_name())
    last_name = factory.LazyFunction(lambda: fake.last_name())
    document_type = "CC"
    document_number = factory.LazyFunction(lambda: str(fake.random_int(min=100000, max=9999999999)))
    phone = factory.LazyFunction(lambda: f"+57{fake.msisdn()[:10]}")
    email = factory.LazyFunction(lambda: fake.email())
    birthdate = factory.LazyFunction(lambda: fake.date_of_birth(minimum_age=1, maximum_age=90).isoformat())
    gender = factory.LazyFunction(lambda: fake.random_element(["male", "female"]))
    address = factory.LazyFunction(lambda: fake.address())
    city = factory.LazyFunction(lambda: fake.city())
    insurance_provider = factory.LazyFunction(
        lambda: fake.random_element(["Sura EPS", "Nueva EPS", "Sanitas", "Coomeva", "Salud Total"])
    )
    blood_type = factory.LazyFunction(
        lambda: fake.random_element(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
    )
