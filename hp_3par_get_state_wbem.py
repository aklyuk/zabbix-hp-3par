#!/usr/bin/python3
#  -*- coding: utf-8 -*-

import os
import time
import argparse
import sys
import json
import subprocess
import logging
import logging.handlers
from re import findall
import pywbem
import paramiko



# Создаем лог-объект
LOG_FILENAME = "/tmp/hp_3par_state.log"
# Берем аргумент содержащий имя СХД и выполняем срез
STORAGE_NAME = sys.argv[5][15:]
hp_logger = logging.getLogger("hp_3par_logger")
hp_logger.setLevel(logging.INFO)

# Устанавливаем хэндлер
hp_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=(1024**2)*10, backupCount=5)
hp_formatter = logging.Formatter('{0} - %(asctime)s - %(name)s - %(levelname)s - %(message)s'.format(STORAGE_NAME), datefmt = '%Y-%m-%d %H:%M:%S')

# Устанавливаем форматтер для хэндлера
hp_handler.setFormatter(hp_formatter)

# Добавляем хэндлер к лог-объекту
hp_logger.addHandler(hp_handler)





def hp_wbem_connect(hp_user, hp_password, hp_ip, hp_port):
	try:
		wbem_url = "https://{0}:{1}".format(hp_ip, hp_port)
		wbem_connect = pywbem.WBEMConnection(wbem_url, (hp_user, hp_password), default_namespace = "root/tpd", no_verification=True, timeout=50)
		hp_logger.info("WBEM Connection Established Successfully")
		return wbem_connect 
	except Exception as oops:
		hp_logger.error("WBEM Connection Error Occurs".format(oops))
		sys.exit("1000")



def hp_ssh_connect(hp_user, hp_password, hp_ip):
	try:
		hp_ssh_client = paramiko.SSHClient()
		hp_ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		hp_ssh_client.connect(hostname=hp_ip, username=hp_user, password=hp_password, port=22)
		hp_logger.info("SSH Connection Established Successfully")
		return hp_ssh_client
	except Exception as oops:
		hp_logger.error("SSH Connection Error Occurs: {0}".format(oops))
		sys.exit("1000")




def hp_ssh_logout(hp_ssh_client):
	try:
		hp_ssh_client.close()
		hp_logger.info("SSH Connection Closed Successfully")
	except Exception as oops:
		hp_logger.error("SSH Connection Close Error Occurs: {0}".format(oops))




def convert_to_zabbix_json(data):
	output = json.dumps({"data": data}, indent = None, separators = (',',': '))
	return output



def send_data_to_zabbix(zabbix_data, storage_name):
	sender_command = "/usr/bin/zabbix_sender"
	config_path = "/etc/zabbix/zabbix_agentd.conf"
	time_of_create_file = int(time.time())
	temp_file = "/tmp/{0}_{1}.tmp".format(storage_name, time_of_create_file)

	with open(temp_file, "w") as f:
		f.write("")
		f.write("\n".join(zabbix_data))
	send_to_zabbix = subprocess.Popen([sender_command, "-vv", "-c", config_path, "-s", storage_name, "-T", "-i", temp_file], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	send_to_zabbix.wait()
	os.remove(temp_file)
	hp_logger.info(send_to_zabbix.communicate())
	hp_logger.info("ReturnCode = {0}".format(send_to_zabbix.returncode))
	return send_to_zabbix.returncode




def discovery_psu_for_drive_enclosure(hp_connect):
	"""
	Discovering PSU for Drive Enclosures
	"""
	cages = hp_connect.EnumerateInstances("TPD_DriveCage", PropertyList=["Name","ElementName"])
	psuS_of_cages = hp_connect.EnumerateInstances("TPD_CagePowerSupply", PropertyList=["Name","ElementName","SerialNumber", "DeviceID"])

	dict_of_cages = dict()
	for cage in cages:
		dict_of_cages[cage["Name"]] = cage["ElementName"]

	discovered_psu_of_cage = []
	for one_psu_of_cage in psuS_of_cages:
		properties_of_cagePsu = dict()
		properties_of_cagePsu["{#CAGE_NAME}"] = dict_of_cages[one_psu_of_cage["Name"].split("-")[0]]
		properties_of_cagePsu["{#SERIAL_NUMBER_PSU}"] = one_psu_of_cage["SerialNumber"]
		properties_of_cagePsu["{#NUMBER_PSU}"] = one_psu_of_cage["ElementName"]
		properties_of_cagePsu["{#DEVICE_ID}"] = one_psu_of_cage["DeviceID"]

		discovered_psu_of_cage.append(properties_of_cagePsu)

	return convert_to_zabbix_json(discovered_psu_of_cage)




def discovery_psu_for_node_controllers(hp_connect):
	"""
	Discovering PSU for Node Controllers
	"""

	nodes = hp_connect.EnumerateInstances("TPD_NodeSystem", PropertyList=["Name","ElementName"])
	psuS_of_nodes = hp_connect.EnumerateInstances("TPD_NodePowerSupply", PropertyList=["Name","ElementName","SerialNumber","OtherSystemName", "DeviceID"])

	dict_of_nodes = dict()
	for node in nodes:
		dict_of_nodes[node["Name"]] = node["ElementName"] #Соответствие внутреннего имени ноды к читабельному

	discovered_psu_of_node = []
	for one_psu_of_node in psuS_of_nodes:
		properties_of_nodePsu = dict()

		list_of_nodes = dict_of_nodes[one_psu_of_node["Name"].split("-")[0]] #one_psu_of_node["Name"].split("-")[0] - системное имя ноды
		""" Get other name of node """
		""" When one PSU is connected to two controllers"""
		try:
			if one_psu_of_node["OtherSystemName"] != '':
				list_of_nodes = list_of_nodes + ', ' + dict_of_nodes[one_psu_of_node["OtherSystemName"]]
		except KeyError as oops:
			hp_logger.info("This PSU {0} is connected to only one controller".format(one_psu_of_node["Name"]))

		properties_of_nodePsu["{#NODE_NAME}"] = list_of_nodes
		properties_of_nodePsu["{#SERIAL_NUMBER_PSU}"] = one_psu_of_node["SerialNumber"]
		properties_of_nodePsu["{#NUMBER_PSU}"] = one_psu_of_node["ElementName"]
		properties_of_nodePsu["{#DEVICE_ID}"] = one_psu_of_node["DeviceID"]

		discovered_psu_of_node.append(properties_of_nodePsu)

	return convert_to_zabbix_json(discovered_psu_of_node)



def discovering_resources(hp_user, hp_password, hp_ip, hp_port, storage_name, list_CIM_classes):
	hp_connect = hp_wbem_connect(hp_user, hp_password, hp_ip, hp_port)

	list_CIM_classes.remove('TPD_CagePowerSupply')
	list_CIM_classes.remove('TPD_NodePowerSupply')

	xer = []
	try:
		for CIM_class in list_CIM_classes:
			instances = hp_connect.EnumerateInstances(CIM_class, PropertyList=["Name","ElementName","DeviceID", "Tag", "SerialNumber", "Manufacturer"])

			discovered_instances = []
			for instance in instances:
				properties_instances_list = dict()
				if ['TPD_Fan', 'TPD_Battery'].count(CIM_class) == 1:
					properties_instances_list["{#DEVICE_ID}"] = instance["DeviceID"]
					discovered_instances.append(properties_instances_list)
				elif ['TPD_DiskDrive', 'TPD_DriveCage', 'TPD_NodeSystem', 'TPD_DynamicStoragePool', 'TPD_SASPort', 'TPD_FCPort', 'TPD_EthernetPort'].count(CIM_class) == 1:
					properties_instances_list["{#ELEMENT_NAME}"] = instance["ElementName"]
					discovered_instances.append(properties_instances_list)
				elif ['TPD_IDEDrive', 'TPD_PCICard'].count(CIM_class) == 1:
					properties_instances_list["{#TAG}"] = instance["Tag"]
					if ['TPD_PCICard'].count(CIM_class) == 1:
						properties_instances_list["{#MANUFACTURER}"] = instance["Manufacturer"]
					discovered_instances.append(properties_instances_list)
				elif ['TPD_PhysicalMemory'].count(CIM_class) == 1:
					properties_instances_list["{#SERIAL_NUMBER}"] = instance["SerialNumber"]
					discovered_instances.append(properties_instances_list)
				else:
					properties_instances_list["{#NAME}"] = instance["Name"]
					properties_instances_list["{#ELEMENT_NAME}"] = instance["ElementName"]
					discovered_instances.append(properties_instances_list)

			converted_instances = convert_to_zabbix_json(discovered_instances)
			timestampnow = int(time.time())
			xer.append("%s %s %s %s" % (storage_name, CIM_class[4:], timestampnow, converted_instances))


		xer.append("%s %s %s %s" % (storage_name, "CagePowerSupply", timestampnow, discovery_psu_for_drive_enclosure(hp_connect)))
		xer.append("%s %s %s %s" % (storage_name, "NodePowerSupply", timestampnow, discovery_psu_for_node_controllers(hp_connect)))
	except pywbem.exceptions.TimeoutError as oops:
		hp_logger.info("Timeout Error occurs in discovery - {0}".format(oops))
		sys.exit("1100")
	except pywbem.exceptions.AuthError as oops:
		hp_logger.error("AuthError occurs in discovery - {0}".format(oops))
		sys.exit("1100")
	except Exception as oops:
		hp_logger.error("An error occurs in discovery - {0}".format(oops))
		sys.exit("1000")

	return send_data_to_zabbix(xer, storage_name)



def get_status_resources(hp_user, hp_password, hp_ip, hp_port, storage_name, list_CIM_classes):
	hp_connect = hp_wbem_connect(hp_user, hp_password, hp_ip, hp_port)

	state_of_instances = []

	try:
		for CIM_class in list_CIM_classes:
			time_stamp_now = int(time.time())
			state_of_concrete_instances = hp_connect.EnumerateInstances(CIM_class, PropertyList=["OperationalStatus","HealthState", "DeviceID", "ElementName", "Tag", "SerialNumber", "SystemLED", "OtherOperationalStatus"])
			for instance in state_of_concrete_instances:
				if ['TPD_Fan', 'TPD_Battery', 'TPD_CagePowerSupply', 'TPD_NodePowerSupply'].count(CIM_class) == 1:
					key_health_status = "health.{0}.[{1}]".format(CIM_class[4:], instance["DeviceID"])# Делаем срез строки, чтобы избавиться от TPD_
					key_oper_status = "oper.{0}.[{1}]".format(CIM_class[4:], instance["DeviceID"])

					state_of_instances.append("%s %s %s %s" % (storage_name, key_health_status, time_stamp_now, instance["HealthState"]))
					state_of_instances.append("%s %s %s %s" % (storage_name, key_oper_status, time_stamp_now, instance["OperationalStatus"][0]))

					#if ['TPD_PowerSupply'].count(CIM_class) == 1:
						#key_ac_status = "ac.{0}.[{1}]".format(CIM_class[4:], instance["DeviceID"])
						#key_dc_status = "dc.{0}.[{1}]".format(CIM_class[4:], instance["DeviceID"])

						#state_of_instances.append("%s %s %s %s" % (storage_name, key_ac_status, time_stamp_now, instance["ACStatus"]))
						#state_of_instances.append("%s %s %s %s" % (storage_name, key_dc_status, time_stamp_now, instance["DCStatus"]))

				if ['TPD_NodeSystem', 'TPD_DriveCage', 'TPD_DiskDrive', 'TPD_DynamicStoragePool', 'TPD_SASPort', 'TPD_FCPort', 'TPD_EthernetPort'].count(CIM_class) == 1:
					key_health_status = "health.{0}.[{1}]".format(CIM_class[4:], instance["ElementName"])
					key_oper_status = "oper.{0}.[{1}]".format(CIM_class[4:], instance["ElementName"])

					state_of_instances.append("%s %s %s %s" % (storage_name, key_health_status, time_stamp_now, instance["HealthState"]))
					state_of_instances.append("%s %s %s %s" % (storage_name, key_oper_status, time_stamp_now, instance["OperationalStatus"][0]))

					if ['TPD_NodeSystem'].count(CIM_class) == 1:
						key_system_led = "led.{0}.[{1}]".format(CIM_class[4:], instance["ElementName"])
						state_of_instances.append("%s %s %s %s" % (storage_name, key_system_led, time_stamp_now, instance["SystemLED"]))
					elif ['TPD_SASPort', 'TPD_FCPort', 'TPD_EthernetPort'].count(CIM_class) == 1:
						key_other_oper_status = "other.oper.{0}.[{1}]".format(CIM_class[4:], instance["ElementName"])
						state_of_instances.append("%s %s %s %s" % (storage_name, key_other_oper_status, time_stamp_now, instance["OtherOperationalStatus"]))

				if ['TPD_IDEDrive', 'TPD_PCICard'].count(CIM_class) == 1:
					key_oper_status = "oper.{0}.[{1}]".format(CIM_class[4:], instance["Tag"])
					state_of_instances.append("%s %s %s %s" % (storage_name, key_oper_status, time_stamp_now, instance["OperationalStatus"][0]))

				if ['TPD_PhysicalMemory'].count(CIM_class) == 1:
					key_oper_status = "oper.{0}.[{1}]".format(CIM_class[4:], instance["SerialNumber"])
					state_of_instances.append("%s %s %s %s" % (storage_name, key_oper_status, time_stamp_now, instance["OperationalStatus"][0]))

	except pywbem.exceptions.TimeoutError as oops:
		hp_logger.info("Timeout Error occurs in getting status - {0}".format(oops))
		sys.exit("1100")
	except pywbem.exceptions.AuthError as oops:
		hp_logger.error("AuthError occurs in getting status - {0}".format(oops))
		sys.exit("1100")
	except Exception as oops:
		hp_logger.error("An error occurs in getting status - {0}".format(oops))
		sys.exit("1000")

	return send_data_to_zabbix(state_of_instances, storage_name)




def get_overprovisioning(hp_user, hp_password, hp_ip, hp_port, storage_name):
	hp_wbem_connection = hp_wbem_connect(hp_user, hp_password, hp_ip, hp_port)
	hp_ssh_connection = hp_ssh_connect(hp_user, hp_password, hp_ip)

	cpg_overprovisioning = []
	time_stamp_now = int(time.time())

	try:
		CPGs = hp_wbem_connection.EnumerateInstances('TPD_DynamicStoragePool', PropertyList=["ElementName"])

		for cpg in CPGs:
			stdin, stdout, stderr = hp_ssh_connection.exec_command('showspace -cpg {0}'.format(cpg["ElementName"]))
			overprv_raw_value = stdout.read()
			overprv_raw_value = overprv_raw_value.decode("utf-8")# Конвертируем из байтовой строки в обчную строку
			overprv_raw_value = overprv_raw_value.split("\n")
			overprv_raw_value = overprv_raw_value[3]

			overprv_raw_value = overprv_raw_value.split(' ')
			value_overprv = float(overprv_raw_value[-1:][0])#Отрезаем все элементы списка кроме последнего.Из полученного списка забираем единственный элемент и к float приводим
			key_overprv = "overprv.DynamicStoragePool.[{0}]".format(cpg["ElementName"])
			cpg_overprovisioning.append("%s %s %s %f" % (storage_name, key_overprv, time_stamp_now, value_overprv))
	except Exception as oops:
		hp_logger.error("An error occurs in overprovision - {0}".format(oops))
		sys.exit("1000")

	hp_ssh_logout(hp_ssh_connection)

	return send_data_to_zabbix(cpg_overprovisioning, storage_name)



#def remove_probel(xer):
#	lenght = len(xer)
#	index = 0
#
#	while index < lenght:
#		if xer[index] == '':
#			del xer[index]
#			lenght = lenght - 1
#		else:
#			index += 1
#	return xer



def main():
	hp_parser = argparse.ArgumentParser()
	hp_parser.add_argument('--hp_ip', action="store", required=True)
	hp_parser.add_argument('--hp_port', action="store", required=False)
	hp_parser.add_argument('--hp_user', action="store", required=True)
	hp_parser.add_argument('--hp_password', action="store", required=True)
	hp_parser.add_argument('--storage_name', action="store", required=True)

	group = hp_parser.add_mutually_exclusive_group(required=True)
	group.add_argument('--discovery', action ='store_true')
	group.add_argument('--status', action='store_true')
	group.add_argument('--overprovisioning', action='store_true')
	group.add_argument('--psu', action='store_true')
	arguments = hp_parser.parse_args()


	list_CIM_classes = ['TPD_DynamicStoragePool', 'TPD_NodeSystem', 'TPD_DriveCage', 'TPD_DiskDrive', 'TPD_CagePowerSupply', 'TPD_NodePowerSupply', 'TPD_Battery', 'TPD_Fan', 'TPD_IDEDrive', 'TPD_PhysicalMemory', 'TPD_SASPort', 'TPD_FCPort', 'TPD_EthernetPort', 'TPD_PCICard']

#	hp_connect = wbem_connect(arguments.hp_user, arguments.hp_password, arguments.hp_ip, arguments.hp_port)

	if arguments.discovery:
		hp_logger.info("********************************* Discovery is starting *********************************")
		result_discovery = discovering_resources(arguments.hp_user, arguments.hp_password, arguments.hp_ip, arguments.hp_port, arguments.storage_name, list_CIM_classes)
		hp_logger.info("********************************* Discovery is ended *********************************")
		print (result_discovery)
	elif arguments.status:
		hp_logger.info("********************************* Get Status is starting *********************************")
		result_status = get_status_resources(arguments.hp_user, arguments.hp_password, arguments.hp_ip, arguments.hp_port, arguments.storage_name, list_CIM_classes)
		hp_logger.info("********************************* Get Status is ended *********************************")
		print (result_status)
	elif arguments.overprovisioning:
		hp_logger.info("********************************* Get overprovisioning is starting *********************************")
		result_status = get_overprovisioning(arguments.hp_user, arguments.hp_password, arguments.hp_ip, arguments.hp_port, arguments.storage_name)
		hp_logger.info("********************************* Get overprovisioning is ended *********************************")
		print(result_status)
	elif arguments.psu:
		result_status = discovery_psu(arguments.hp_user, arguments.hp_password, arguments.hp_ip, arguments.hp_port, arguments.storage_name)


if __name__ == "__main__":
	main()
