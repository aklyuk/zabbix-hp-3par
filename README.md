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
On zabbix web-interface on "storage_name_in_zabbix_web_interface" must be new items and triggers.

8) On zabbix proxy or on zabbix servers need run **zabbix_proxy -R config_cache_reload** (zabbix_server -R config_cache_reload).

9) In Linux-console on zabbix-server or zabbix-proxy need run this command to get value of metrics. Scripts must return value 0 in case of success:
```
./hp_3par_get_state_wbem.py --hp_ip=xxx.xxx.xxx.xxx --hp_port=5989 --hp_user=username_on_storagedevice --hp_password='xxxxxxxxxxxx' --storage_name=storage_name_in_zabbix_web_interface --status
```
10) If you have executed this script from console from user root or from another user, please check access permission on file **/tmp/hp_3par_state.log**. It must be allow read/ write to user zabbix.

**Return code 1 or 2 is zabbix_sender return code. Read here - https://www.zabbix.com/documentation/4.4/manpages/zabbix_sender**

P.S.
Overprovisioning on a DynamicStoragePool work not correct. I can't recommend to use this metric.

P.P.S.
Monitoring SFP will be added later.
