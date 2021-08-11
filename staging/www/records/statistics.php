<?php


require('../main.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();
$login = new Login($web_users, true, $ipc);
$system = new AdditiveInjector($ipc);
$self_dir = '/records';
$self = "$self_dir/statistics.php";
$dir_path = "/config/records/stats/";
$left_col = '12em';
$records = new RecordFiles($system);
$stats_config = new IpcConfig($ipc, 'statistics');

$end_date=date('Y-m-d');
$end_time=date('H:i', strtotime('1/1/2000'));
$start_date=date('Y-m-d', strtotime('-1 month'));
$start_time=date('H:i', strtotime('1/1/2000'));
$months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];


$page_selector = 'bio_tank_stats';
$data_column = 2;
$tank_column = 3;
if (isset($_GET['bio'])){
    $page_selector = 'bio_tank_stats';
    $data_column = 2;
    $tank_column = 3;
    $special_tank_column = 3;
    $self = $self . '?bio';
    $config_name_long = 'bio';
    $config_name = 'bio';
}
if (isset($_GET['dsl'])){
    $page_selector = 'dsl_tank_stats';
    $data_column = 4;
    $tank_column = 5;
    $special_tank_column = 5;
    $self = $self . '?dsl';
    $config_name_long = 'diesel';
    $config_name = 'dsl';
}
if (isset($_GET['blend'])){
    $page_selector = 'blend_stats';
    $data_column = 6;
    $tank_column = 3;
    $special_tank_column = 7;
    $self = $self . '?blend';
    $config_name_long = 'blend';
    $config_name = 'blend';
}

require('math.php');

function build_list ($dir_file_names) {
    $compare = function ($a, $b) {

       $a_info = pathinfo($a);
       $a_name = $a_info['basename'];
       $a_month_text = substr($a_name, 0, 3);
       $a_year_text = substr($a_name, 4, 4);

       $b_info = pathinfo($b);
       $b_name = $b_info['basename'];
       $b_month_text = substr($b_name, 0, 3);
       $b_year_text = substr($b_name, 4, 4);

       $a_date = strtotime("$a_month_text $a_year_text");
       $b_date = strtotime("$b_month_text $b_year_text");
        
       # Reverse sort (most recent first)
       return $b_date - $a_date;
    };

    $result=$dir_file_names;

    usort($result, $compare);

    return $result;
}

if (isset($_GET['download'])) {
   # Same as below, but GET.

   if (!file_exists($path)) {
      ErrorPage::show('The records you requested do not exist.');
   }

   # Hardcoded header file, at the moment

   header('Content-Type: text/plain; charset=us-ascii');
   header('Content-Type: application/octet-stream');
   header('Content-Disposition: attachment; filename=" ' .basename($path). '"');
   header('Expires: 0');
   header('Pragma: public');
   header('Content-Length: ' . filesize($path));
   header('Content-Description: File Transfer');
   header('Cache-Control: must-revalidate');

   readfile($path); 
   die;
}

$page = new Page($system);
$page->header('Record Statistics');

if (count($records)) {
     
     $page->begin_section($system->get_param_value('Product Name') . ' Records');
     echo $form->get_html();
     $page->end_section();

} else {
    # Empty file list
    $page->begin_section($system->get_param_value('Product Name') . ' Records');
    echo '<p>There are no record files on this system.</p>';
    $page->end_section();
}


$stats_form = new Form($self); 
$page->begin_section('Custom Record Statistics');
echo '<center><h3>This statistics page compares the bioblenders ' . $config_name_long . '-meter vs the tank monitors ' .  $config_name_long . '-tank reading.</h3></center>';

if (is_dir($dir_path)) {
    $dir_file_names = array_values(array_diff(scandir($dir_path),array('..','.')));
    //print_var($dir_file_names);
    $new_dir_file_names=array();

    # get rid of any bad filenames/folders
    foreach ($dir_file_names as $i=>$file) {
        if (is_numeric(substr($dir_file_names[$i], 4, 4))) {
            foreach ($months as $month) {
                if (strtolower(substr($dir_file_names[$i], 0, 3))==$month) {
                    //array_push($new_dir_file_names,$dir_file_names[$i]);
                    $new_dir_file_names[] = $dir_file_names[$i];
                    break;
                }
            }
        }
    }
    //print_var($new_dir_file_names);
}

do {
    if (sizeof($new_dir_file_names)<=0){
        #$page->begin_section('Record Statistics');
        # There aren't any record files to show.
        echo '<p>There are no ' . $config_name_long . '-tank vs ' . $config_name_long . '-meter statistics records on this system.<br>Try adding a ' . $config_name_long . ' tank under the configuration page</p>';
        # echo '<p>Record statistics has not yet been implemented for this system.</p>';
        break;
    }
    $file_data = array();
    $file_dates = array();
    $file_times = array();
    $row_num = array();
    $good_row_num = array();
    $null_row_num = array();
    //$file_tags = array();
    $div_index = array();
    $custom_data = array();
    $invalid_range = false;
    $actual_start_datetime = 0;
    $actual_end_datetime = 0;
    $width_correction = 0.5;
    $margin_value = 5;
    $num_of_records = count($new_dir_file_names);
    if ($num_of_records>4) {
        $num_of_records = 4;
    }

    $width_percent = (100-($margin_value/$num_of_records)*($num_of_records-1))/$num_of_records-$width_correction;
    if ($num_of_records==1) {
        $height = ($width_percent/100)*700;
    } else {
        $height = ($width_percent/100)*1500;
    }
    $margin_percent = $margin_value/$num_of_records;
    $sorted_file_names = build_list($new_dir_file_names);

    # Go through each file in the statistics directory and extract the data from each CSV file
    foreach ($sorted_file_names as $i => $file) {
        if (($handle = fopen($dir_path . $file, "r")) !== FALSE) {
            $row_num[$i] = 0;
            $good_row_num[$i] = 0;
            $null_row_num[$i] = 0;
            while (($row = fgetcsv($handle)) !== FALSE){
                //$file_data[$i][$good_row_num]  = strval($row[3]);
                if ((abs($row[$data_column]) < $stats_config[$config_name . '_error_ignore']) && ($row[$tank_column] > $stats_config['min_' . $config_name . '_tank_reading_stats'])){
                    #if (substr(strval($row[$tank_column]), 0 , 4) == 'good') {
                    $file_dates[$i][$good_row_num[$i]] = strval($row[0]);
                    $file_times[$i][$good_row_num[$i]] = strval($row[1]);
                    $file_data[$i][$good_row_num[$i]]  = strval($row[$data_column]);
                    $good_row_num[$i]++;
                }
                if ($row[$data_column]==-1 && $row[$blend_column]==-1){
                    $null_row_num[$i]++;
                }
                $row_num[$i]++;
            }
            $div_index[] = str_replace('.CSV','',$file);
        }
        fclose($handle);
    }


    if (array_sum($null_row_num)==array_sum($row_num)){
        #$page->begin_section('Record Statistics');
        # There aren't any record files to show.
        echo '<p>There are no ' . $config_name_long . '-tank vs ' . $config_name_long . '-meter statistics records on this system.<br>Try adding a ' . $config_name_long . ' tank under the configuration page</p>';
        # echo '<p>Record statistics has not yet been implemented for this system.</p>';
        break;
    }

    if (count($file_data)<=0){
        echo '<p>There are no good ' . $config_name_long . '-tank vs ' . $config_name_long . '-meter stats records on this system. (' . strval(array_sum($row_num)-array_sum($good_row_num)-array_sum($null_row_num)) . ' bad or insignificant one(s))</p>';
        echo '<p>This may be due to insufficent ' . $config_name_long . ' tank level movement on the record, a delivery occuring, or an exceptionally large error between the ' . $config_name_long . ' tank level and the ' . $config_name_long . ' meter</p>';
        break;
    }

    if (isset($_POST['submit_hist'])) {
        //print_var($_POST);
        
        $start_date = $_POST['start_config']['date'] ?? false;
        $start_time = $_POST['start_config']['time'] ?? false;

        $end_date = $_POST['end_config']['date'] ?? false;
        $end_time = $_POST['end_config']['time'] ?? false;

        $start_datetime = date('Y-m-d H:i:s', strtotime("$start_date $start_time"));
        $end_datetime = date('Y-m-d H:i:s', strtotime("$end_date $end_time"));

        //print_var("start datetime: ".$start_datetime);
        //print_var("end datetime: ".$end_datetime);
        if ($start_datetime>$end_datetime) {
            $temp = $start_date;
            $start_date = $end_date;
            $end_date = $temp;
            $temp = $start_time;
            $start_time = $end_time;
            $end_time = $temp;
        }
    
        $start_month_year = date('Y-m', strtotime($start_date));
        $end_month_year = date('Y-m', strtotime($end_date));
        //print_var("start date time: ".strtotime($start_date)." start month/year time: ".strtotime($start_month_year));

        $start_index = -1;
        $end_index = -1;
        foreach ($sorted_file_names as $i=>$f_name) {
            $f_month_text = substr($f_name, 0, 3);
            $f_year_text  = substr($f_name, 4, 4);
            //print_var("start date: ".$start_date." start date time: ".strtotime($start_date));
            //print_var("end date: ".$end_date." end date time: ".strtotime($end_date));
            $file_datetime = date('Y-m', strtotime("$f_year_text $f_month_text"));
            //print_var("file date: ".$file_datetime." file date time: ".strtotime($file_datetime));
            

            if (strtotime($file_datetime)>=strtotime($start_month_year)) {
                $start_index = $i;
                //print_var("start: ".$i);
            }
            if (strtotime($file_datetime)>strtotime($end_month_year)) {
                $end_index = $i;
                //print_var("end: ".$i);
            }
        }
        $end_index+=1;
        if ($start_index == -1 || $end_index == sizeof($sorted_file_names)) {
            $invalid_range = true;
        } else {
            //print_var("start index: ".$start_index);
            //print_var("end index: ".$end_index);
            for ($i=sizeof($file_data); $i>= 0;$i--) {
                //print_var("dump: ".$i);
                if ($i < $end_index || $i > $start_index) continue;
                $result=array();
                foreach ($file_data[$i] as $key=>$value ) {
                    $val=$file_dates[$i][$key];
                    $val_2=$file_times[$i][$key];
                    $result[$key]=array($value,$val,$val_2);
                }

                if ($i != $end_index && $i != $start_index) {
                    # we are neither at the starting month or ending month, so we can just push the entire array in
                    //print_var("add entire record");
                    //print_var($file_data[$i]);
                    $custom_data = array_merge($custom_data,$result);
                } else {
                    # we need to find where we start
                    $month_s_index = 0;
                    $month_e_index = sizeof($file_data[$i]);
                    $array_to_merge = array();
                    $start_index_match_found = false;

                    if ($i == $start_index) {
                        foreach ($file_data[$i] as $s => $start) {
                            # compare day
                            if (strtotime($file_dates[$i][$s])==strtotime($start_date)) {
                                # if equal, find the closest time which chronologically comes 1 after the time given by the user
                                if (strtotime($file_times[$i][$s])>=strtotime($start_time)) {
                                    $month_s_index = $s;
                                    $start_index_match_found = true;
                                    break;
                                }
                            }
                            if (strtotime($file_dates[$i][$s])>strtotime($start_date)) {
                                # if greater than, slice off all the data from the dates after the date given by the user
                                $month_s_index = $s;
                                $start_index_match_found = true;
                                break;
                            }
                        }
                        if ($start_index_match_found == false) {
                            $month_s_index=sizeof($file_data[$i]);
                        }
                    }
                    if ($i == $end_index) {
                        foreach ($file_data[$i] as $e => $end) {
                            # compare day
                            if (strtotime($file_dates[$i][$e])==strtotime($end_date)) {
                                # if equal, find the closest time which chronologically comes 1 after the time given by the user
                                if (strtotime($file_times[$i][$e])>=strtotime($end_time)) {
                                    $month_e_index = $e;
                                    break;
                                }
                            }
                            if (strtotime($file_dates[$i][$e])>strtotime($end_date)) {
                                # if greater than, slice off all the data from the dates after the date given by the user
                                $month_e_index = $e;
                                break;
                            }
                        }
                    }
                    //print_var('month index: '.$i.'   month start index: '.$month_s_index.'   month end index: '.$month_e_index);
                    $array_to_merge = array_slice($result, $month_s_index, $month_e_index-$month_s_index);
                    $custom_data = array_merge($custom_data,$array_to_merge);
                }
            }
        }
            # generate the html for the custom histogram here
            $custom_histogram = new DivElement();

            # Go through each file in the statistics directory and generate the div elemnt of each CSV file
            $custom_histogram->set_attribute('id', 'custom_hist');
            $custom_histogram->append_attribute('class', 'data vertical-separators');
            $custom_histogram->add_style('width', '100%');
            //$custom_histogram->add_style('height', strval($height) . 'px');
            $custom_histogram->add_style('border-style', 'solid');
            //$custom_histogram->add_style('display', 'inline-flex');
            $custom_histogram->add_style('margin-bottom', strval($margin_percent) . '%');
            $custom_histogram->add_style('margin-right', strval($margin_percent) . '%');
            //print_var($custom_data);
    }
    $custom_form = new Form($self);
    
    $custom_form->add_child(new WhiteSpace('100%'));
    $custom_form->add_child($custom_histogram);


    $start = new FormRow(
        'Start Date and Time',
        [
           new DateBox('start_date', 'start_config[date]', $start_date),
           new PlainText('&nbsp; at '),
           new TimeBox('start_time', 'start_config[time]', $start_time)
        ],
        $left_col,
        $start_date_time
     );
     
    $start->set_attribute('id', 'dtdiv');
    $start->add_style('display','inline');
    
    $stats_form->add_child($start);

    $space = new WhiteSpace('10%');
    $stats_form->add_child($space);

    $end = new FormRow(
        'End Date and Time',
        [
           new DateBox('end_date', 'end_config[date]', $end_date),
           new PlainText('&nbsp; at '),
           new TimeBox('end_time', 'end_config[time]', $end_time)
        ],
        $left_col,
        $end_date_time
     );
     
    $end->set_attribute('id', 'dtdiv2');
    $end->add_style('display','inline');
    $stats_form->add_child($end);
    

    $stats_form->add_child(new FormRow(
        '&nbsp;',
        new SubmitButton('submit_hist', false, 'Generate Histogram'),
        $left_col
     ))->add_style('display','inline-flex');

    echo $stats_form->get_html();
    echo $custom_form->get_html();

    $page->end_section();
    //print_var($custom_data);    
    $page->begin_section('Monthly Record Statistics');

   #print_var($sorted_file_names);

   #print_var($width_percent);
   $histograms = new DivElement();

   # Go through each file in the statistics directory and generate the div elemnt of each CSV file
   foreach ($sorted_file_names as $i => $file) {
        $histogram = new DivElement();
        $histogram->set_attribute('id', $div_index[$i]);
        $histogram->append_attribute('class', 'data vertical-separators');
        $histogram->add_style('width', strval($width_percent) . '%');
        $histogram->add_style('height', strval($height) . 'px');
        $histogram->add_style('border-style', 'solid');
        $histogram->add_style('display', 'inline-flex');
        $histogram->add_style('margin-bottom', strval($margin_percent) . '%');
        if ($i<(count($sorted_file_names)-1)) {
            if (($i+1) % 4 !=0) {
                $histogram->add_style('margin-right', strval($margin_percent) . '%');
            }
        }
        $histograms->add_child($histogram);
   }
   #print_var($div_index);
   //print_var($file_data);

   
   echo $histograms->get_html();

   #print_var(str_replace('.CSV','',$dir_files));

} while (0);

$page->end_section();

$page->footer();

?>
<head>
    <script src="/scripts/plotly-latest.min.js"></script>
</head>


<script>
    //Histogram generating script based on the div element generated froms statistics directory
    function getMeanAndSD (array) {
        const n = array.length
        const mean = array.reduce((a, b) => a + b) / n
        return [
            mean,
            Math.sqrt(array.map(x => Math.pow(x - mean, 2)).reduce((a, b) => a + b) / n)
        ];
    }
    function roundedToFixed(_float, _digits) {
        var rounded = Math.pow(10, _digits);
        return (Math.round(_float * rounded) / rounded).toFixed(_digits);
    }

    var minimum_data_points = 20;
    var passed_array = 
        <?php echo json_encode($file_data); ?>;
    var div_index = 
        <?php echo json_encode($div_index); ?>;
    var window_width = window.innerWidth;
    var warning_label;


    for (i=0;i<passed_array.length;i++) {
        if (passed_array[i].length>=minimum_data_points) {
            warning_label = '';
        } else {
            warning_label = 'WARNING: NOT ENOUGH DATA POINTS ('+passed_array[i].length+')';
        }

        var x = (passed_array[i].map(Number)).map(x => x * 100);

        var [mean,sd] = getMeanAndSD(x);

        var layout = {
            autosize: true,
            margin:{
                l: (50/2560)*window_width,
                r: (45/2560)*window_width,
                b: (40/2560)*window_width,
                t: (75/2560)*window_width,
                pad: 1
            },
            title: {
                text: '<b>'+div_index[i]+'</b>' + '  mean:    '+roundedToFixed(mean,3)+' <br>          std-dev: '+roundedToFixed(sd,3)+'</br>',
                font: {
                    family: 'Courier New, monospace',
                    size: (24/2560)*window_width
                },
                xref: 'paper',
                x: 0.05,
            },
            xaxis: {
                title: {
                    text: 'Percent Error',
                    font: {
                        family: 'Courier New, monospace',
                        size: (18/2560)*window_width,
                        color: '#7f7f7f'
                    }
                },
            },
            yaxis: {
                title: {
                    text: 'Number of Records',
                    font: {
                        family: 'Courier New, monospace',
                        size: (18/2560)*window_width,
                        color: '#7f7f7f'
                    }
                }
            },
            showlegend: true,
            legend: {
                x: 1,
                y: 0.5
            },
            annotations: [
                {
                    xref: 'paper',
                    yref: 'paper',
                    text: warning_label,
                    showarrow: false,
                    font: {
                        size: ((50/2560)*window_width)/passed_array.length
                    },
                }
            ]
        };

        var trace = {
            x: x,
            name: "Data <br>points<br>-->"+x.length,
            type: 'histogram',
        };
        var data = [trace];
        Plotly.newPlot(div_index[i], data, layout)
    /*
        } else {
            var layout = {
                autosize: true,
                margin:{
                    l: (50/2560)*window_width,
                    r: (45/2560)*window_width,
                    b: (40/2560)*window_width,
                    t: (75/2560)*window_width,
                    pad: 1
                },
                title: {
                    text: '<b>'+div_index[i]+'</b>',
                    font: {
                        family: 'Courier New, monospace',
                        size: (24/2560)*window_width
                    },
                    xref: 'paper',
                    x: 0.05,
                },
                xaxis: {
                    'visible': false
                },
                yaxis: {
                    'visible': false
                },
                annotations: [
                    {
                        xref: 'paper',
                        yref: 'paper',
                        text: 'Not enough data points ('+passed_array[i].length+')',
                        showarrow: false,
                        font: {
                            size: (50/2560)*window_width
                        },
                    }
                ]
            };

            var trace = {
                x: x,
                type: 'histogram',
            };
            var data = [];
            Plotly.newPlot(div_index[i], data, layout)
            
        }
        */
    }

    var custom_arrays = 
        <?php echo json_encode($custom_data); ?>;
    div_name = 'custom_hist';
    var custom_array = custom_arrays.map(function(value,index) { return value[0]; });
    var custom_warning_label
    if (custom_array.length>=minimum_data_points) {
        custom_warning_label = '';
    } else {
        custom_warning_label = 'WARNING: NOT ENOUGH DATA POINTS ('+custom_array.length+')';
    }
    if (custom_array.length>0) {

        var x = (custom_array.map(Number)).map(x => x * 100);

        var [mean,sd] = getMeanAndSD(x);
        var actual_start_date = custom_arrays[0][1];
        var actual_start_time = custom_arrays[0][2];
        var actual_end_date = custom_arrays[custom_arrays.length-1][1];
        var actual_end_time = custom_arrays[custom_arrays.length-1][2];

        var layout = {
            autosize: true,
            margin:{
                l: (50/2560)*window_width,
                r: (45/2560)*window_width,
                b: (40/2560)*window_width,
                t: (75/2560)*window_width,
                pad: 1
            },
            title: {
                text: '<b> Custom Histogram </b>' + '  mean:    '+roundedToFixed(mean,3)+
                '                          Actual starting date and time: '+actual_start_date+
                ' '+actual_start_time+' <br>                    std-dev: '+roundedToFixed(sd,3)+
                '                              Actual ending date and time: '+actual_end_date+' '+actual_end_time+'</br>',

                font: {
                    family: 'Courier New, monospace',
                    size: (24/2560)*window_width
                },
                xref: 'paper',
                x: 0.05,
            },
            xaxis: {
                title: {
                    text: 'Percent Error',
                    font: {
                        family: 'Courier New, monospace',
                        size: (18/2560)*window_width,
                        color: '#7f7f7f'
                    }
                },
            },
            yaxis: {
                title: {
                    text: 'Number of Records',
                    font: {
                        family: 'Courier New, monospace',
                        size: (18/2560)*window_width,
                        color: '#7f7f7f'
                    }
                }
            },
            showlegend: true,
            legend: {
                x: 1,
                y: 0.5
            },
            annotations: [
                {
                    xref: 'paper',
                    yref: 'paper',
                    text: custom_warning_label,
                    showarrow: false,
                    font: {
                        size: (50/2560)*window_width
                    },
                }
            ]
        };

        var trace = {
            x: x,
            name: "Data <br>points<br>-->"+x.length,
            type: 'histogram',
        };
        var data = [trace];
        Plotly.newPlot(div_name, data, layout)
    
    } else {
        var invalid_range = 
            <?php echo json_encode($invalid_range); ?>;
        plot_message = invalid_range ? 'Invalid date range' : 'Not enough data points ('+custom_array.length+')';
        var layout = {
            autosize: true,
            margin:{
                l: (50/2560)*window_width,
                r: (45/2560)*window_width,
                b: (40/2560)*window_width,
                t: (75/2560)*window_width,
                pad: 1
            },
            title: {
                text: '<b> Custom Histogram </b>',
                font: {
                    family: 'Courier New, monospace',
                    size: (24/2560)*window_width
                },
                xref: 'paper',
                x: 0.05,
            },
            xaxis: {
                'visible': false
            },
            yaxis: {
                'visible': false
            },
            annotations: [
                {
                    xref: 'paper',
                    yref: 'paper',
                    text: plot_message,
                    showarrow: false,
                    font: {
                        size: (50/2560)*window_width
                    },
                }
            ]
        };

        var trace = {
            x: x,
            type: 'histogram',
        };
        var data = [];
        Plotly.newPlot(div_name, data, layout)
    }

</script>
