<?php
/* Copyright (C) 2010-2013 by Contrail Consortium. */



require_once('../__init__.php');
require_module('service');
require_module('service/factory');

try {
	if (!isset($_SESSION['uid'])) {
		throw new Exception('User not logged in');
	}
	$sid = $_GET['sid'];
	$service_data = ServiceData::getServiceById($sid);
	$service = ServiceFactory::create($service_data);
    //echo var_dump($service);
	if($service->getUID() !== $_SESSION['uid']) {
	    throw new Exception('Not allowed');
	}
	$update = $service->checkManagerInstance();
	if ($update) {
		$service_data = ServiceData::getServiceById($sid);
	}
    //$service['state'] = 'RUNNING';
    //var_dump($service);
	echo json_encode($service->toArray());
} catch (Exception $e) {
	echo json_encode(array(
		'error' => $e->getMessage(),
	));
}

?>
