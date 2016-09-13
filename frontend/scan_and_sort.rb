#!/usr/bin/ruby

require 'optparse'
require 'ostruct'

options = OpenStruct.new
options.library = []
options.inplace = false
options.encoding = "utf8"
options.transfer_type = :auto
options.verbose = false

parser = OptionParser.new
parser.banner = "Usage: frontend [options] []"
parser.on("-h", "--help", "Prints this help") {|val| options["help"] = true}
parser.on("--scan nb", Integer, "Scan doc.") { |val| options[:scan] = val }
parser.on("--move cur_category,new_category,filename", Array, "Move doc.") {|val| options[:move] = val}

parser.parse(*ARGV)

$path_papers = "/home/aghiti/wip/sort_scan_image/papers/unknown/"
$nb_sheet_paper = 1 
$num_sheet_paper = 0 

def search_scanner()
	return "plustek:libusb:002:009"
end

# Get the number of scanned doc not already treated.
# (normally should not a lot since paper sorter runs
# as a daemon using inotify.
def get_nb_scanned_doc(path)
	nb_scanned_doc = 0
	# while File.exist?(File.join(path_papers, "scan_and_sort#{nb_scanned_doc}.tmp") do
	while !Dir.glob("#{path}/scan_and_sort#{nb_scanned_doc}*.tmp").empty? do
		nb_scanned_doc = nb_scanned_doc + 1
	end 
	print("frontend: document number %s\n" % nb_scanned_doc)
	return nb_scanned_doc
end

def scan_doc(nb_doc)
	puts "frontend: scanning..."

	# TODO Multipage document.
	# If this is the first page of the document, create a new number of 
	# document. Otherwise, take the same and suffix a, b, c...etc. 
	# TODO more than just one letter for big documents.
	cur_num_doc = nb_doc.to_s + ('a'.ord + $num_sheet_paper).chr
	scan_options = "-d #{search_scanner()} --res 300 --format pnm -x 215 -y 297 --warmup-time 1"
	print("scanimage #{scan_options} > /tmp/scan_and_sort#{cur_num_doc}.tmp")
	ret = `scanimage #{scan_options} > /tmp/scan_and_sort#{cur_num_doc}.tmp`
	ret_value = `echo $?`.tr("\n", "")
	
	if ret_value != "0" then
		print("frontend: Scan failed #{ret_value}.")
	end

	puts "frontend: scan ok."

	return nb_doc
end

# For the moment, a filename is "category_timestamp"
# get '/sample/move/:cur_category/:right_category/:filename' do
def move_paper(cur_category, right_category, filename)
	timestamp = filename.split("_")[1]
	new_file_name = "#{right_category}_#{timestamp}"
	path_old = File.join($path_papers, "..", cur_category, filename)
	path_new = File.join($path_papers, "..", right_category, new_file_name)
	print("frontend: Moving #{path_old} to #{path_new}.")
	ret = `mv #{path_old} #{path_new}`
	ret = `mv #{path_old}.txt #{path_new}.txt`
end

# TODO Multipage document.
# post '/sample/document/:action' do
# 	puts "COUCOU IN?"
# 	if params['action'] == "increment" then
# 		$nb_sheet_paper += 1
# 	else
# 		if ($nb_sheet_paper > 1) then
# 			$nb_sheet_paper -= 1
# 		end
# 	end
# 	
# 	update_nb_sheet()
# 	# Must return a different value than one by send_event, otherwise
# 	# we got an error 500 at client side.
# end

def validate_scan()
	$num_sheet_paper += 1

	# If we finished the document, then merge the pages into one and send it to ocr.
	if ($nb_sheet_paper == $num_sheet_paper) then
		nb_doc = get_nb_scanned_doc("/tmp") - 1 
		if ($nb_sheet_paper > 1) then
			cv_str = "convert "
			cv_str += `ls /tmp/scan_and_sort#{nb_doc}*.tmp`.gsub("\n", " ")
			cv_str += " -append #{$path_papers}/scan_and_sort#{nb_doc}.tmp"
			ret = `#{cv_str}`
		else
			ret = `cp /tmp/scan_and_sort#{nb_doc}a.tmp #{$path_papers}/scan_and_sort#{nb_doc}.tmp`
		end	
	end
end

if (options["help"]) then
	print("frontend: Help")
	puts parser.to_s
	exit true
end

if (options["scan"] >= 1) then
	$nb_sheet_paper = options["scan"].to_i
	$num_sheet_paper = 0
	nb_doc = get_nb_scanned_doc("/tmp")
	while ($num_sheet_paper < $nb_sheet_paper)
		scan_doc(nb_doc)
		ret = `eog /tmp/scan_and_sort#{nb_doc}#{('a'.ord + $num_sheet_paper).chr}.tmp`
		print("frontend: Is the scan ok ? (Y/n)")
		answer = STDIN.gets.chomp()
		if (answer == "" or answer.downcase() == "y") then
			validate_scan()
		else
			ret = `rm /tmp/scan_and_sort#{nb_doc}*`
			break
		end
	end	
elsif (options["move"]) then
	print("frontend: Move")
	move_paper(options["move"][0], options["move"][1], options["move"][2])
end
