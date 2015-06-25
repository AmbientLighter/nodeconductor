Resources list
--------------

Use */api/resources/* to get a list of all the resources that a user can see.
Only resources that have agreed and actual SLA values are shown.

Supported filters are:

- ?hostname **deprecated**, use ?name instead; - case insensitive matching of a name
- ?service_name - case insensitive matching of a service name
- ?customer_name - case insensitive matching of a customer name
- ?customer_native_name - case insensitive matching of a customer native name
- ?customer_abbreviation - case insensitive matching of a customer abbreviation
- ?project_name - case insensitive matching of a project name
- ?project_group_name - case insensitive matching of a project_group name
- ?agreed_sla - exact match of SLA numbers
- ?actual_sla - exact match of SLA numbers
- ?project_groups -  **deprecated**, use ?project_group_name instead

Ordering can be done by the following fields (prefix with **-** for descending order):

- ?o=hostname **deprecated**, use ?o=name instead;
- ?o=template_name
- ?o=customer_name
- ?o=customer_abbreviation
- ?o=customer_native_name
- ?o=project_name
- ?o=project_group_name
- ?o=agreed_sla
- ?o=actual_sla
- ?o=template__name - **deprecated**, use ?o=template_name instead
- ?o=project__customer__name - **deprecated**, use ?o=customer_name instead
- ?o=project__name - **deprecated**, use ?o=project_name instead
- ?o=project__project_groups__name - **deprecated**, use ?o=project_group_name instead
- ?o=slas__value - **deprecated**, use ?o=actual_sla instead

Response example:

.. code-block:: http

    GET /api/resources/ HTTP/1.1

    HTTP/1.0 200 OK
    Content-Type: application/json
    Vary: Accept
    Allow: GET, HEAD, OPTIONS
    X-Result-Count: 1

    [
        {
            "url": "http://example.com/api/resources/0356addb8e9742e7b984ebcaf5912c6b/",
            "uuid": "0356addb8e9742e7b984ebcaf5912c6b",
            "state": "Offline",
            "name": "FromBackup777",
            "template_name": "cirros-0.3.1-x86_64",
            "customer_name": "Customer A",
            "customer_native_name": "Customer A (native)",
            "customer_abbreviation": "CA",
            "project_name": "STG/Backups",
            "project_uuid": "19e4581367cb4f93bf77c21f68fbc2d1",
            "project_url": "http://example.com/api/projects/19e4581367cb4f93bf77c21f68fbc2d1/",
            "project_groups": [],
            "agreed_sla": "95",
            "actual_sla": null,
            "service_type": "IaaS",
            "access_information": []
        }
    ]


SLA periods
^^^^^^^^^^^

Service list is displaying current SLAs for each of the items. By default, SLA period is set to the current month. To
change the period pass it as a query argument:

- ?period=YYYY-MM - return a list with SLAs for a given month
- ?period=YYYY - return a list with SLAs for a given year

In all cases all currently running resources are returned, if SLA for the given period is not known or not present, it
will be shown as **null** in the response.

SLA events
^^^^^^^^^^

Service SLAs are connected with occurrences of events. To get a list of such events issue a GET request to
*/resources/<service_uuid>/events/*. Optionally period can be supplied using the format defined above.

The output contains a list of states and timestamps when the state was reached. The list is sorted in descending order
by the timestamp.

Example output:

.. code-block:: javascript

    [
        {
            "timestamp": 1418043540,
            "state": "U"
        },
        {
            "timestamp": 1417928550,
            "state": "D"
        },
        {
            "timestamp": 1417928490,
            "state": "U"
        }
    ]
