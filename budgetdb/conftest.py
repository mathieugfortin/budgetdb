import pytest
from datetime import date
from django.contrib.auth import get_user_model
from crum import impersonate
from budgetdb.models import *

User = get_user_model()

@pytest.fixture
def cad(db):
    return Currency.objects.create(name="Canadian Dollar", name_short="CAD", symbol="$", priority=1)

@pytest.fixture
def usd(db):
    return Currency.objects.create(name="American Dollar", name_short="USD", symbol="$", priority=2)

@pytest.fixture
def user_a_without_prefs(db):
    return User.objects.create_user(
        email='owner@example.com', 
        password='secreta',
        first_name='test_user_a_Owner',
        is_active=True,
        email_verified=True
    )

@pytest.fixture
def user_friend_without_prefs(user_a):
    user_friend = User.objects.create_user(
        email='friend@example.com', 
        password='secretfriend',
        first_name='test_user_friend',
        is_active=True,
        email_verified=True
    )
    user_friend.friends.add(user_a)
    user_friend.save()
    user_a.friends.add(user_friend)
    user_a.save()
    return user_friend

@pytest.fixture
def user_b_without_prefs(db):
    return User.objects.create_user(
        email='admin@example.com', 
        password='secreta',
        first_name='test_user_b_Admin',
        is_active=True,
        email_verified=True
    )

@pytest.fixture
def user_bad_without_prefs(db):
    return User.objects.create_user(
        email='nobody@example.com', 
        password='secretbad',
        first_name='test_user_bad',
        is_active=True,
        email_verified=True
    )


@pytest.fixture
def user_a(user_a_without_prefs, cad):
    with impersonate(user_a_without_prefs):
        Preference.objects.create(
            user=user_a_without_prefs,
            slider_start=date(2026, 1, 1),
            slider_stop=date(2026, 12, 31),
            currency_prefered=cad
        )
    return user_a_without_prefs

@pytest.fixture
def user_friend(user_friend_without_prefs, cad):
    with impersonate(user_friend_without_prefs):
        Preference.objects.create(
            user=user_friend_without_prefs,
            slider_start=date(2026, 1, 1),
            slider_stop=date(2026, 12, 31),
            currency_prefered=cad
        )
    return user_friend_without_prefs

@pytest.fixture
def user_b(user_b_without_prefs, cad):
    with impersonate(user_b_without_prefs):
        Preference.objects.create(
            user=user_b_without_prefs,
            slider_start=date(2026, 1, 1),
            slider_stop=date(2026, 12, 31),
            currency_prefered=cad
        )
    return user_b_without_prefs


@pytest.fixture
def user_bad(user_bad_without_prefs, cad):
    with impersonate(user_bad_without_prefs):
        Preference.objects.create(
            user=user_bad_without_prefs,
            slider_start=date(2026, 1, 1),
            slider_stop=date(2026, 12, 31),
            currency_prefered=cad
        )
    return user_bad_without_prefs

@pytest.fixture
def host_1(user_a):
    with impersonate(user_a):
        return AccountHost.objects.create(name="Bank 1")

@pytest.fixture
def acc_a(user_a, host_1, cad, user_friend):
    with impersonate(user_a):
        acc = Account.objects.create(
            name="account a",
            account_host=host_1,
            currency=cad,
            # owner=user_a, # should be done by base class' save()
            date_open=date(2026, 1, 1)
        )
    acc.users_admin.add(user_friend)
    acc.save()
    return acc

@pytest.fixture
def acc_b(user_a, host_1, cad, user_friend):
    with impersonate(user_a):
        acc = Account.objects.create(
            name="account b",
            account_host=host_1,
            currency=cad,
            ofx_flip_sign=True,
            ofx_acct_id = '2345',
            ofx_org = 'orga',
            date_open=date(2026, 1, 1)
        )
    acc.users_view.add(user_friend)
    acc.save()
    return acc

@pytest.fixture
def acc_c(user_a, host_1, cad):
    with impersonate(user_a):
        return Account.objects.create(
            name="account c",
            account_host=host_1,
            currency=cad,
            ofx_flip_sign=True,
            ofx_acct_id = '3456',
            ofx_org = 'orgb',
            date_open=date(2026, 1, 1)
        )

@pytest.fixture
def acc_da(user_a, host_1, cad, user_friend):
    with impersonate(user_a):
        acc = Account.objects.create(
            name="deleted account a",
            account_host=host_1,
            currency=cad,
            ofx_flip_sign=True,
            ofx_acct_id = '4567',
            ofx_org = 'orgb',
            date_open=date(2026, 1, 1)
        )
        acc.users_admin.add(user_friend)
        acc.save()
        acc.soft_delete()
        return acc

@pytest.fixture
def acc_db(user_a, host_1, cad, user_friend):
    with impersonate(user_a):
        acc = Account.objects.create(
            name="deleted account b",
            account_host=host_1,
            currency=cad,
            ofx_flip_sign=True,
            ofx_acct_id = '4567',
            ofx_org = 'orgb',
            date_open=date(2026, 1, 1)
        )
        acc.users_view.add(user_friend)
        acc.save()
        acc.soft_delete()
        return acc

@pytest.fixture
def cat_type_a(user_a):
    with impersonate(user_a):
        return CatType.objects.create(
                name="catType A",
                owner=self.user_a,
            )

@pytest.fixture
def cat_type_b(user_a):
    with impersonate(user_a):
        return CatType.objects.create(
                name="catType A",
                owner=self.user_a,
            )

@pytest.fixture
def cat1_a(user_a, cat_type_a):
    with impersonate(user_a):
        return Cat1.objects.create(
                name="cat1 A", 
                owner=self.user_a,
                cattype=self.cat_type_a,
            )

@pytest.fixture
def cat1_b(user_a, cat_type_a):
    with impersonate(user_a):
        return Cat1.objects.create(
                name="cat1 B", 
                owner=self.user_a,
                cattype=self.cat_type_b,
            )

@pytest.fixture
def cat1_c(user_a, cat_type_a):
    with impersonate(user_a):
        return Cat1.objects.create(
                name="cat1 C", 
                owner=self.user_a,
                cattype=self.cat_type_a,
            )

@pytest.fixture
def cat2_a1(user_a, cat_type_a):
    with impersonate(user_a):
        return Cat2.objects.create(
                name="cat2 A1", 
                cat1=self.cat1_a, 
                cattype=self.cat_type_a,
                owner=self.user_a,
            )

@pytest.fixture
def cat2_a2(user_a, cat_type_a):
    with impersonate(user_a):
        return Cat2.objects.create(
                name="cat2 A2", 
                cat1=self.cat1_a, 
                cattype=self.cat_type_a,
                owner=self.user_a,
            )

@pytest.fixture
def cat2_a3(user_a, cat_type_a):
    with impersonate(user_a):
        return Cat2.objects.create(
                name="cat2 A3", 
                cattype=self.cat_type_a,
                cat1=self.cat1_a, 
                owner=self.user_a,
            )            


@pytest.fixture
def cat2_b1(user_a, cat_type_a):
    with impersonate(user_a):
        return Cat2.objects.create(
                cattype=self.cat_type_b,
                name="cat2 B1", 
                cat1=self.cat1_b, 
                owner=self.user_a,
            )


@pytest.fixture
def cat2_b2(user_a, cat_type_a):
    with impersonate(user_a):
        return Cat2.objects.create(
                cattype=self.cat_type_b,
                name="cat2 B2", 
                cat1=self.cat1_b, 
                owner=self.user_a,
            ) 

@pytest.fixture
def cat2_c1(user_a, cat_type_a):
    with impersonate(user_a):
        return Cat2.objects.create(
                cattype=self.cat_type_a,
                name="cat2 C1", 
                cat1=self.cat1_c, 
                owner=self.user_a,
            )



