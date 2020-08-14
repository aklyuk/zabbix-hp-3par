# zabbix-hp-3par

Python script for monitoring HP 3PAR storages. Tested on HPE_3PAR 8450,  HPE_3PAR 20840_R2

1) You must create user on storages, as example < username_on_storagedevice >. **Role** of this user is **browse**
2) On template on sectin Macros you need to set these macros:
- {$HP_USER} - user on storage, as example < username_on_storagedevice >
- {$HP_PASSWORD} - password of username_on_storagedevice
- {$SMI_S_PORT} - SMI-S port. By default is 5989.

3) In agent configuration file, **/etc/zabbix/zabbix_agentd.conf** must be set parameter **ServerActive=xxx.xxx.xxx.xxx**
4) Scirpt must be copied to zabbix-server, if you will be monitoring throught zabbix-server OR must be copied to zabbix-proxy, if you will be monitoring throught zabbix-proxy.
5) zabbix-sender utility must be installed
6) Python modules pywbem, paramiko must be installed
7) In Linux-console on zabbix-server or zabbix-proxy need run this command to make discovery by hand. Script must return value 0 in case of success:
```
./hp_3par_get_state_wbem.py --hp_ip=xxx.xxx.xxx.xxx --hp_port=5989 --hp_user=username_on_storagedevice --hp_password='xxxxxxxxxxxx' --storage_name=storage_name_in_zabbix_web_interface --discovery
```
