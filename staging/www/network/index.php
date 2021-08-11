<?php

require('../main.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();
$login = new Login($web_users, true, $ipc);
$system = new AdditiveInjector($ipc);

$login->admin_check();

if (isset($_POST['submit'])) {
   $mode = get_post('mode');
   $ip = get_post('ip');
   $subnet = get_post('subnet');
   $gateway = get_post('gateway');
   $dns = get_post('dns');
   $hostname = get_post('hostname');

   # Validate these
   if (filter_var($mode, FILTER_VALIDATE_INT) === false) die;
   if (filter_var($ip, FILTER_VALIDATE_IP) === false) $errors['ip'] = 'Invalid address.';
   if (filter_var($subnet, FILTER_VALIDATE_IP) === false) $errors['subnet'] = 'Invalid subnet mask.';
   if (filter_var($gateway, FILTER_VALIDATE_IP) === false) $errors['gateway'] = 'Invalid default gateway.';
   if (filter_var($dns, FILTER_VALIDATE_IP) === false) $errors['dns'] = 'Invalid DNS server address.';

   if (preg_match('/^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$/', $hostname) !== 1) {
      $errors['hostname'] = 'Invalid hostname';
   }

   # Change up
   $mode = (int)$mode;
   $page = new Page($system);
   $page->header('Network');
   $page->begin_section('Network Configuration');
   echo '<p>The network settings are being applied.</p>';
   if ($mode === 0) {
      echo '<p>Click <a href="http://' . $ip . ':6144/">here</a> to access the Bioblender at its new address.</p>';
   }
   $page->end_section();
   $page->footer();
   flush();
   ob_flush();

   $ipc->request([
      'request_type' => 'set_network',
      'dhcp' => $mode,
      'ip_address' => $ip,
      'subnet_mask' => $subnet,
      'gateway' => $gateway,
      'dns' => $dns,
      'hostname' => $hostname
   ]);

   die;
} else {
   $data = $ipc->request([
      'request_type' => 'get_network'
   ]);

   $mode = $data['dhcp'];
   $ip = $data['ip_address'];
   $subnet = $data['subnet_mask'];
   $gateway = $data['gateway'];
   $dns = $data['dns'];
   $hostname = $data['hostname'];
}

$page = new Page($system);

$page->header('Network');

$page->begin_section('Network Configuration');

$form = new Form('/network/index.php');
$left_col = '13em';

$form->add_child(new FormRow(
   'Mode',
   new SelectBox('mode', false, [
      '0' => 'Static Configuration',
      '1' => 'Automatic Configuration (DHCP)'
   ], $mode),
   $left_col
));

$form->add_child(new FormRow(
   'IP Address',
   new TextBox('ip', false, $ip, 13, 15),
   $left_col,
   $errors['ip']
));

$form->add_child(new FormRow(
   'Subnet Mask',
   new TextBox('subnet', false, $subnet, 13, 15),
   $left_col,
   $errors['submit']
));

$form->add_child(new FormRow(
   'Default Gateway',
   new TextBox('gateway', false, $gateway, 13, 15),
   $left_col,
   $errors['submit']
));

$form->add_child(new FormRow(
   'DNS Server',
   new TextBox('dns', false, $dns, 13, 15),
   $left_col,
   $errors['submit']
));

$form->add_child(new FormRow(
   'Host Name',
   new TextBox('hostname', false, $hostname, 23, 63),
   $left_col,
   $errors['hostname']
));

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('submit', false, 'Save Settings'),
   $left_col
));

echo $form->get_html();

$page->end_section();

$page->footer();

?>
