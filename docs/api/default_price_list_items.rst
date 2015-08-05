Default price list items
------------------------

To get a list of default price list items, run GET against **/api/price-list-items/** as authenticated user.


Price lists can be filtered by:
 - ?key=<string>
 - ?item_type=<string> has to be from list of available item_types
   (available options: 'flavor', 'storage', 'license-os', 'license-application', 'network', 'support')
 - ?service_content_type=<string> name of service type(Examples: 'openstack.openstackservice, 'oracle.oracleservice')


Response example:

.. code-block:: http

    GET /api/price-list-items/
    Accept: application/json
    Content-Type: application/json
    Authorization: Token c84d653b9ec92c6cbac41c706593e66f567a7fa4
    Host: example.com


    [
        {
            "url": "http://example.com/api/default-price-list-items/c2ef5e11d8484bfaac84acbc31cca953/",
            "uuid": "c2ef5e11d8484bfaac84acbc31cca953",
            "key": "price list item 7",
            "item_type": "flavor",
            "value": "10.00000000",
            "units": "USD",
            "service_content_type": "openstack.openstackservice"
        }
    ]


