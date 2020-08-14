# zabbix-hp-3par

Python script for monitoring HP 3PAR storages. Tested on HPE_3PAR 8450,  HPE_3PAR 20840_R2

1) You must create user on storages, as example "zabbix_storage_user". **Role** of this user is **browse**
2) On template on sectin Macros you need to set these macros:
- {$HP_USER} - user on storage, as example "zabbix_storage_user"
- {$HP_PASSWORD} - password of zabbix_storage_user
- {$SMI_S_PORT} - SMI-S port. By default is 5989.

3) In agent configuration file, **/etc/zabbix/zabbix_agentd.conf** must be set parameter **ServerActive=xxx.xxx.xxx.xxx**
4) Scirpt must be copied to zabbix-server, if you will be monitoring throught zabbix-server OR must be copied to zabbix-proxy, if you will be monitoring throught zabbix-proxy.
5) zabbix-sender utility must be installed
