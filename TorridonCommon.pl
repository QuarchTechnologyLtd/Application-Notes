#!/usr/bin/perl
#
# Author: Andy Norrie
# Date:   27-04-2011
# Requirements: Win32::SerialPort 
# (Uses same interface as Device::SerialPort linux module so can be ported)
#
# Version: 1.0
#
# Description:  This perl script is for demonstrating issuing commands to
# multiple torridon modules via a Torridon array controller using a serial 
# connection. Data from the serial port is logged to the specified file (Quarch.log).  
# The logfile can then be parsed with other programs for reporting purposes.
# 

use strict;

use if ($^O eq "MSWin32"), 'Win32::SerialPort';

use if ($^O eq "linux"), 'Device::SerialPort';

use Net::Telnet ();
            # use Win32 serial port module

# 1 = Log commands and responses, 0 = No logging
my $LogText = 0;
# 1 = Config:Terminal set to 'SCRIPT', 0 = Config:Terminal set to 'USER' mode
my $ScriptMode = 0;
my $Connection;
my $PORT;
# Subroutine to send a command to the attached device.  The serial port must be open
# and the device ready to receive commands.  This function will not block, even if the
# module does not respond
# string SendTorridonCommand ($SerialPort, $CommandString)

sub SendTorridonCommand() {
	my($Connection, $Command) = @_;

if(index( $Connection, "SerialPort") != -1){
	
	my $Response = "";
	my $Section = "";
	my $Timeout = 0;
	my $TimeoutLimit = 50;		# 1 = approx 10ms timout delay

	if ($LogText) {
		# Print out the command for logging
		print $Command . "\n";
	}
	# Write the command to the serial port
	
	$Connection->write($Command . "\r");

	# Discard any echoed characters of the command
	# By waiting for the <CR><LF> return at the end of the command echo
	if ($ScriptMode) {
		$Connection->are_match ("\n");	
	}
	else {
		$Connection->are_match ("\r\n");	
	}
	until ("" ne $Section || $Timeout > $TimeoutLimit) {
		# Look for the line feed section
		$Section = $Connection->lookfor;

		# Track a 2 second timeout
		select(undef, undef, undef, 0.01);
		$Timeout++;
	}

	# If the line feed was seen, as expected
	if ($Timeout <= $TimeoutLimit) {
		$Connection->are_match (">");
		$Timeout = 0;
		until ("" ne $Response || $Timeout > $TimeoutLimit) {
			# Look for the cursor
			$Response = $Connection->lookfor;

			# Track a 2 second timeout
			select(undef, undef, undef, 0.01);
			$Timeout++;
		}

		if ($LogText) {
			# Print out the full response for logging
			# Add the cursor back as the loop above will have removed it
			print $Response . ">";
		}
	
		# If the cursor was NOT seen (response did not end correctly)
		if ($Timeout > $TimeoutLimit) {
			if ($LogText) {
				# Log the error
				print "FAIL: (1)Module timed out without releasing the bus\n";
			}

			return $Response . "\nFAIL: (2)Module timed out without releasing the bus";
		}
		# Else the command completed fully
		else {
			# Return the response from the module
			$Response = strip($Response);
			return $Response;
		}
	}
	# Command line feed was not returned
	else {
		if ($LogText) {
			# Log the error
			print "FAIL: (3)No response from the module\n";
		}
		return "FAIL: (4)No response from the module";
	}
	}
	
	if(index($Connection, "Telnet") != -1){  
	
	#my($Connection, $Command) = @_;
	
	my @Response;
	my $Responses;

	if ($LogText) {
		# Print out the command for logging
		print $Command . "\n";
	}

	# Write the command to the telnet port
	@Response = $Connection->cmd($Command . "\r\n");
	select(undef, undef, undef, 0.5);
	if ($LogText) {
		# Print out the full response for logging
		# Add the cursor back as the loop above will have removed it
		#print @Response;
		#print ">";
	}
	#@Response  = strip(@Response);
	#print @Response;
	$Responses = join("\r\n" , @Response);
	#print $Responses;
	return $Responses;
	
	}
	
}


sub strip(){
	my $value = shift;
	$value  =~ s/^\s+|\s+$//g;
	return $value;
}

sub striparray(){
	my @array = shift;
	my @strippedarray = grep(s/\s*$//g, @array);
	return @strippedarray;

}

sub OpenConnection(){
 
	my $PORT= $_[0];

#print $PORT;
 if(index( $PORT, "COM") != -1){

 		# **** Serial port to use ****
my($first, $rest) = split(/:/, $PORT, 2);
#print $rest . "\n\n";

if($^O eq "MSWin32"){

	$Connection = Win32::SerialPort->new ($rest) || die "Can't Open $PORT: $!";
}

elsif($^O eq "linux"){

	$Connection = Device::SerialPort->new ($rest) || die "Can't Open $PORT: $!";
}

$Connection->baudrate(19200)   || die "failed setting baudrate";
$Connection->databits(8)       || die "failed setting databits";
$Connection->stopbits(1)       || die "failed setting stopbits";
$Connection->handshake("none") || die "failed setting handshake";
$Connection->parity("none")    || die "failed setting parity";
#SerialPort defers change to serial settings until write_settings() 
#method which validates settings and then implements changes
$Connection->write_settings    || die "no settings";
#print $Connection;

 return $Connection;
 
 }
 if(index( $PORT, "ttyS") != -1){

 		# **** Serial port to use ****
my($first, $rest) = split(/:/, $PORT, 2);
#print $rest . "\n\n";

if($^O eq "MSWin32"){

	$Connection = Win32::SerialPort->new ($rest) || die "Can't Open $PORT: $!";
}

elsif($^O eq "linux"){

	$Connection = Device::SerialPort->new ($rest) || die "Can't Open $PORT: $!";
}

$Connection->baudrate(19200)   || die "failed setting baudrate";
$Connection->databits(8)       || die "failed setting databits";
$Connection->stopbits(1)       || die "failed setting stopbits";
$Connection->handshake("none") || die "failed setting handshake";
$Connection->parity("none")    || die "failed setting parity";
#SerialPort defers change to serial settings until write_settings() 
#method which validates settings and then implements changes
$Connection->write_settings    || die "no settings";
#print $Connection;

 return $Connection;
 
 }
 
 
if(index($PORT, "Telnet") != -1){

my($first, $rest) = split(/:/, $PORT, 2);

	my $Conn;
	
if($^O eq "MSWin32"){

	# Open the connection
	$Conn = new Net::Telnet (Timeout => 5,
			         Binmode => 1,
			         Cmd_remove_mode => 1,
			         Input_record_separator => "\r\n",
			         Output_record_separator => "",
			         Prompt => '/^[>]/m',
			         Telnetmode => 0,
						Dump_log => 'c:\\temp\tellog.txt');
						
						$Conn->open ($rest);
	
	select(undef, undef, undef, 0.5);
	$Conn->cmd ("");
	select(undef, undef, undef, 0.5);
	
	$Connection = $Conn;
				
}

elsif($^O eq "linux"){

	# Open the connection
	$Conn = new Net::Telnet (Timeout => 5,
			         Binmode => 1,
			         Cmd_remove_mode => 1,
			         Input_record_separator => "\r\n",
			         Output_record_separator => "",
			         Prompt => '/^[>]/m',
			         Telnetmode => 0,
				
				 Dump_log => '/home\telleg.txt');
				 
				 $Conn->open ($rest);
	
	select(undef, undef, undef, 0.5);
	$Conn->cmd ("");
	select(undef, undef, undef, 0.5);
	
	$Connection = $Conn;
}
	
	
}

 }

1;