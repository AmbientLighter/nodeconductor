import logging

from django.contrib.auth.models import Group
from django.utils.encoding import python_2_unicode_compatible
from django_auth_ldap.backend import populate_user
from django.dispatch import receiver

from django.db import models


logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class LdapToGroup(models.Model):
    class Meta(object):
        verbose_name = "LDAP to Django group mapping"

    ldap_group_name = models.CharField(max_length=80)
    django_group = models.ForeignKey(Group)

    def __str__(self):
        return '%(ldap)s -> %(group)s' % {
                'ldap': self.ldap_group_name,
                'group': self.django_group
        }


@receiver(populate_user)
def synchronise_user_groups(**kwargs):
    """
    Synchronise Django group membership base on user's ldap groups and configured mappings.
    """
    logger.debug('Synchronising user groups from ldap.')
    ldap_user = kwargs['ldap_user']
    user = kwargs['user']
    # get all the user groups marked for management
    managed_user_groups = LdapToGroup.objects.filter(django_group__user=user)
    # go over all the current user groups and make sure they are correct
    for group in managed_user_groups:
        if group.ldap_group_name in ldap_user.group_names:
            logger.debug('User is still in the group %s' % group)
        else:
            print 'User has left the group %s' % group
            logger.debug('User has left the group %s' % group)
            user.groups.remove(group.django_group)

    # add groups present in ldap that have a mapping
    for group in LdapToGroup.objects.exclude(django_group__user=user).filter(ldap_group_name__in=ldap_user.group_names):
        logger.debug('Adding missing group membership %s' % group)
        user.groups.add(group.django_group)
