# zabbix-hp-3par

Python script for monitoring HP 3PAR storages. Tested on HPE_3PAR 8450,  HPE_3PAR 20840_R2

First, you must create user on storages, as example zabbix_storage_user. **Role** of this user is **browse**
Second, in template in sectin Macros you need to set these macros:
- {$HP_USER} - user on storage, as example zabbix_storage_user
- {$HP_PASSWORD} - password of zabbix_storage_user
- {$SMI_S_PORT} - SMI-S port. By dafault is 5989.

In agent configuration file, **/etc/zabbix/zabbix_agentd.conf** must be set parameter **ServerActive=xxx.xxx.xxx.xxx**

Scirpt must be copied to zabbix-server, if you will be monitoring throught zabbix-server or to zabbix-proxy, if you will be monitoring throught zabbix-proxy.

