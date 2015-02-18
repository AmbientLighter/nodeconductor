Introduction
------------

NodeConductor supports backups in a generic way - if a model (like VM Instance, Project, Customer) implements a
backup strategy, it can be used as a source of backup data.

The backups can be created either manually or by setting a schedule for regular automatic backups.

Backup
------

To create a backup, issue the following POST request:

.. code-block:: http

    POST /api/backups/ HTTP/1.1
    Content-Type: application/json
    Accept: application/json
    Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
    Host: example.com

    {
        "backup_source": "http://example.com/api/instances/a04a26e46def4724a0841abcb81926ac/",
        "description": "a new manual backup"
    }

On creation of backup it's projected size is validated against a remaining storage quota.

Example of a created backup representation:

.. code-block:: http

    GET /api/backups/7441df421d5443118af257da0f719533/ HTTP/1.1
    Content-Type: application/json
    Accept: application/json
    Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
    Host: example.com

    {
        "url": "http://example.com/api/backups/7441df421d5443118af257da0f719533/",
        "backup_source": "http://example.com/api/instances/a04a26e46def4724a0841abcb81926ac/",
        "description": "a new manual backup",
        "created_at": "2014-10-19T20:43:37.370Z",
        "kept_until": null,
        "state": "Backing up"
        "backup_schedule": "http://example.com/api/backup-schedules/075c3525b9af42e08f54c3ccf87e998a/"
    }

Please note, that backups can be both manual and automatic, triggered by the schedule.
In the first case, **backup_schedule** field will be **null**, in the latter - contain a link to the schedule.

Backup has a state, currently supported states are:

- Ready
- Backing up
- Restoring
- Deleting
- Erred

Backup actions
--------------

Each created backup supports several operations. Only users with write access to backup source can use them.
Operations are listed below:

- **/api/backup/<backup_uuid>/restore/** - restore a specified backup. Restoring a backup can take user input.
  Restoration is available only for backups in state ``READY``. If backup is not ready endpoint will return response
  with stat 409 - conflict.
  Supported inputs for VM Instance:

  - flavor - url to a flavor used for restoration. Mandatory.
  - hostname - Hostname of the restored VM. Optional (equals to the hostname of the original VM by default).

- **/api/backup/<backup_uuid>/delete/** - delete a specified backup

If a backup is in a state that prohibits this operation, it will be returned in error message of the response.

Backup schedules
----------------

To perform backups on a regular basis, it is possible to define a backup schedule. Example of a request:

.. code-block:: http

    POST /api/backup-schedules/ HTTP/1.1
    Content-Type: application/json
    Accept: application/json
    Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
    Host: example.com

    {
        "backup_source": "/api/instances/430abd492a384f9bbce5f6b999ac766c/",
        "description": "schedule description",
        "retention_time": 0,
        "maximal_number_of_backups": 10,
        "schedule": "1 1 1 1 1",
        "is_active": true
    }

For schedule to work, it should be activated - it's flag is_active set to true. If it's not, it won't be used
for triggering the next backups. Schedule will be deactivated if backup fails.

- **retention time** is a duration in days during which backup is preserved.
- **maximal_number_of_backups** is a maximal number of active backups connected to this schedule.
- **schedule** is a backup schedule defined in a cron format.

Activating/deactivating a schedule
----------------------------------

A schedule can be it two states: active or not. Non-active states are not used for scheduling the new tasks.
Only users with right access to backup schedule source can activate or deactivate schedule.

To activate a backup schedule, issue POST request to **/api/backup-schedules/<UUID>/activate/**. Note that
if a schedule is already active, this will result in 409 code.

To deactivate a backup schedule, issue POST request to **/api/backup-schedules/<UUID>/deactivate/**. Note that
if a schedule was already deactivated, this will result in 409 code.
