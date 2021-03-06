from django.core.urlresolvers import reverse
import factory
import factory.fuzzy

from nodeconductor.quotas import models


class QuotaFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Quota

    limit = factory.fuzzy.FuzzyFloat(low=16.0, high=1024.0)
    usage = factory.LazyAttribute(lambda q: q.limit / 2)
    name = factory.Iterator(['vcpu', 'storage', 'max_instances', 'ram'])

    @classmethod
    def get_list_url(self):
        return 'http://testserver' + reverse('quota-list')

    @classmethod
    def get_url(self, quota, action=None):
        if quota is None:
            quota = QuotaFactory()
        url = 'http://testserver' + reverse('quota-detail', kwargs={'uuid': quota.uuid})
        return url if action is None else url + action + '/'
