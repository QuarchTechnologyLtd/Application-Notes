#!/usr/bin/perl
#
# Author: Andy Norrie
# Date:   27-04-2011
# Requirements: TorridonCommon_Telnet 
#
# Version: 1.0
#
# Description:  This perl script is for demonstrating issuing commands to a
# torridon module using a telnet connection.

use strict;


# Import torridon common functions
# You can edit this file to turn logging on/off.  By default all commands are responses
# are dumped to stdout.  Set "LogText = 0" to turn this off
#


require 'TorridonCommon.pl';


my $Connection;
my $Result;
my $Loop;
my $CurrentState;

# Set your IP address on netBIOS name here!


$Connection = OpenConnection("Telnet:192.168.1.134");
#$Connection = OpenConnection("Serial:COM4"); 
#$Connection = OpenConnection("Serial:/dev/ttyS3");


# Send each command using the form below.  If you are using an Array Controller (rather than a standalone Switch module)
# then you will need to add an address pamameter to the end of each command: <1>

# Ask the module what it is and store the resulting string
#$Result = &SendTorridonCommand ($Connection, "hello? <1>");


QuarchSwitchExample();
#QuarchHotplugExample();
#QuarchPowerMarginingExample();

# Close the Telnet port
$Connection->close;  


sub QuarchPowerMarginingExample{
	print $Connection;
	print "Running the power module example\n\n";

    # Prints out the ID of the attached module
    print "Module Attached is: \n\n";
    print &SendTorridonCommand($Connection,"hello?") . "\n\n";
	sleep(1);
   
    #Set the 5V channel and 12V channel to 5000mV and 12000mV to ensure that they are at the right level
    print "Setting PPM into default voltage state\n\n";
	
    &SendTorridonCommand($Connection,"Sig:5v:Volt 5000");
	
    &SendTorridonCommand($Connection,"Sig:12v:Volt 12000");
    
    #Check the state of the module and Power up if necessary
    print "Checking the State of the Device and power up if necessary\n\n";
	
    $CurrentState = &SendTorridonCommand($Connection,"run:power?");
	
    print "State of the Device:" . ($CurrentState) ."\n\n";
    
    #$CurrentState =~ s/^\s+|\s+$//g;
    # If the outputs are off
    if ($CurrentState eq "OFF"){
        # Power up
		
        &SendTorridonCommand($Connection,"run:power up");
        print"\nPowering the outputs\n\n";        
        # Let the attached device power up fully
        sleep(5);
}
    # Print headers
    print"\nRunning power margining test:\n\n" ;       
    print"Margining Results for 12V rail\n\n";
    print "";

    # Loop through 6 different voltage levels, reducing by 200mV on each loop
    my $TestVoltage = 12000;   
    my $i;
    for ($i = 0; $i<=6; $i++){
        
        # Set the new voltage level
        &SendTorridonCommand($Connection,"Sig:12V:Volt " . $TestVoltage);
        
        # Wait for the voltage rails to settle at the new level        
        sleep(1);
        my $volt = &SendTorridonCommand($Connection,"Measure:Voltage 12V?");
		
        # Request and print the voltage and current measurements
		my $current = &SendTorridonCommand($Connection,"Measure:Current 12V?");
		
        print  $volt .  " = "  .  $current . "\n\n";
        # Decreasing the TestVoltage by 200mv
        $TestVoltage -= 200;
	}
    # Set the 12v level aback to default
    print"Setting the 12V back to default State\n\n";
	
    &SendTorridonCommand($Connection,"Sig:12V:Volt 12000") ;   
    
    # Print headers
    print"Margining Results for 5V rail\n\n";
	
    print "";

    # Loop through 6 different voltage levels, reducing by 200mV on each loop
    $TestVoltage = 5000 ;   
    for($i = 0; $i<=6; $i++){
        
        # Set the new voltage level
        &SendTorridonCommand($Connection,"Sig:5V:Volt " . $TestVoltage);
        
        # Wait for the voltage rails to settle at the new level             
        sleep(1);
        my $volt = &SendTorridonCommand($Connection,"Measure:Voltage 5V?");
		
        # Request and print the voltage and current measurements
		my $current = &SendTorridonCommand($Connection,"Measure:Current 5V?");
		
        print  $volt .  " = "  .  $current . "\n\n";
        
        # Decreasing the TestVoltage by 200mv
        $TestVoltage -= 200;
     }   
    print"Setting the 5V back to default State\n" ;   
    &SendTorridonCommand($Connection,"Sig:5V:Volt 5000");

    print "ALL DONE!";


}

sub QuarchHotplugExample{

	print "Running the hot-plug module example\n\n";
	print "Module Attached is:\n\n";
	print &SendTorridonCommand($Connection,"hello?") . "\n\n"; 


	$Result = &SendTorridonCommand($Connection,"run:power?");    
 
    print "Checking the State of the Device and Power up if necessary\n\n";
	
	print "State of the Device:" . ($Result) . "\n\n";


	if($Result eq "PULLED"){
	
			print "Plugging the device\n\n";
			&SendTorridonCommand($Connection,"run:power up"),
			print "Waiting for power up to complete:\n\n";
			sleep 15;
	}
	
	print "Starting HotPlug cycle:\n\n";

	for(my $i =1; $i <= 6; $i++){
	
			print "HotPlug Cycle: " . $i;
			print "\nPulling the Device\n\n" ;
			# Power down (pull) the device
			&SendTorridonCommand($Connection,"run:power down");
			sleep 15;
			# Power up (plug) the device
			print "\nPlugging the device\n\n";
			&SendTorridonCommand($Connection,"run:power up");


	}
	
	print "ALL DONE!"

}


sub QuarchSwitchExample{


		
	print "Running the physical layer switch example\n\n";
 
	print "Module Attached is:\n\n";

	print &SendTorridonCommand($Connection,"hello?") . "\n\n";

	my $InitialDelay = &SendTorridonCommand($Connection,"CONFig:MUX Delay?");   
    # Checking the existing delay
    print "Current Connection Delay: " . $InitialDelay;

	# Create a new delay, as double the current one, this will be used for the second part of the test
    my $NewDelay = int($InitialDelay)*2;
        
    # Set a Connection between Port 1 and 8 
    print "\nSetting a Connection between Port 1 and Port 8\n\n";
	
    &SendTorridonCommand($Connection,"MUX:CONnect 1 8");
    # Sleep until the connection is in place
    sleep($InitialDelay);
	
	print "Setting a Connection between Port 1 and Port 4\n\n";
	
    &SendTorridonCommand($Connection,"MUX:CONnect 1 4");
    sleep($InitialDelay);
	
	print "Changing the delay to double the existing delay\n\n";
	
    &SendTorridonCommand($Connection,"CONFig:MUX:DELay " . $NewDelay);
	print "new delay is " . $NewDelay . "\n\n";
	
	print"Setting a Connection between Port 1 and Port 8\n\n";
	
    &SendTorridonCommand($Connection,"MUX:CONnect 1 8");
    sleep($NewDelay);
    
    #TODO: Here you would check if your connected equimpent is working correctly
    
    #Set a Connection between Port 1 and 4    
    print"Setting a Connection between Port 1 and Port 4\n\n";
	
    &SendTorridonCommand($Connection,"MUX:CONnect 1 4");
    sleep($NewDelay);
    
    #TODO: Here you would check if your connected equimpent is working correctly
    
    #Set the switch back to initial delay we had at the start
    print "";
    print"Changing the delay back to the old delay\n\n";
    &SendTorridonCommand($Connection,"CONFig:MUX:Delay " . $InitialDelay);

    print "ALL DONE!";

}

 