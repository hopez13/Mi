import xml.etree.ElementTree as ET
import sys

# Parse the XML file and extract symbol CRCs
def parse_xml(file_path):
    tree = ET.parse(file_path)
    return {symbol.get('name'): symbol.get('crc') for symbol in tree.findall(".//elf-symbol")}

# Parse the vmlinux.symvers file and extract symbol CRCs
def parse_symvers(file_path):
    with open(file_path, 'r') as file:
        return {line.split()[1]: line.split()[0] for line in file if len(line.split()) >= 2}

# Read the list of symbols from the sym_names file
def parse_sym_names(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file]

# Validate and convert CRC to integer, returns None if invalid
def validate_crc(crc):
    try:
        crc_int = int(crc, 16)
        # Check if CRC is a valid 32-bit integer
        if 0 <= crc_int < 2**32:
            return crc_int
        else:
            print(f"Warning: CRC value {crc} is not a valid 32-bit value.")
            return None
    except ValueError:
        print(f"Error: Invalid CRC value {crc}.")
        return None

# Compare CRC values and log mismatched symbols
def compare_crcs(xml_symbols, symvers_symbols, target_symbols):
    mismatches = {}
    missing_crcs_in_xml = []  # Track symbols missing CRCs from XML only
    missing_crcs_in_symvers = []  # Track symbols missing from symvers
    matched_count = 0  # Count of successfully matched CRCs
    checked_count = 0  # Count of total checked symbols

    for symbol in target_symbols:
        checked_count += 1  # Increment checked count
        
        # Check for CRC in the XML file
        xml_crc = xml_symbols.get(symbol)

        # Check for missing CRCs: if not found in XML
        if xml_crc is None:
            # If not found in XML, check in symvers
            if symbol in symvers_symbols:
                missing_crcs_in_xml.append(symbol)  # Found in symvers, but missing in XML
            else:
                missing_crcs_in_symvers.append(symbol)  # Not found in both
            continue  # Skip further checks for this symbol
        
        # Proceed only if XML CRC is found
        symvers_crc = symvers_symbols.get(symbol)

        # Validate and compare valid CRCs if symvers_crc is found
        if symvers_crc is not None:
            xml_crc_int = validate_crc(xml_crc)
            symvers_crc_int = validate_crc(symvers_crc)

            # Compare valid CRCs if both are present
            if xml_crc_int is not None and symvers_crc_int is not None:
                if xml_crc_int != symvers_crc_int:
                    mismatches[symbol] = (xml_crc, symvers_crc)
                else:
                    matched_count += 1  # Increment matched count on successful match

    return mismatches, missing_crcs_in_xml, missing_crcs_in_symvers, matched_count, checked_count

# Paths to the files
xml_file = 'abi.xml'
symvers_file = 'module.symvers'
sym_names_file = 'symbols'

# Parse the files
xml_symbols = parse_xml(xml_file)
symvers_symbols = parse_symvers(symvers_file)
target_symbols = parse_sym_names(sym_names_file)

# Compare CRCs
mismatches, missing_crcs_in_xml, missing_crcs_in_symvers, matched_count, total_checked = compare_crcs(xml_symbols, symvers_symbols, target_symbols)

# Output mismatched symbols
if mismatches or missing_crcs_in_xml or missing_crcs_in_symvers:
    if mismatches:
        print("\nMismatched Symbols:")
        for symbol, crcs in mismatches.items():
            print(f"  ➜ Symbol: {symbol}")
            print(f"    ◉ XML CRC:     {crcs[0]}")
            print(f"    ◉ symvers CRC: {crcs[1]}\n")
    
    if not mismatches:
        print("\nNo Mismatched Symbols Found.")

    # Print symbols missing from XML
    print("\nMissing CRCs Found In Symvers:")
    for symbol in missing_crcs_in_xml:
        print(f"  ✦ Symbol: {symbol}")

    # Print symbols missing from both XML and symvers
    print("\nMissing CRCs Not Found In Symvers:")
    for symbol in missing_crcs_in_symvers:
        print(f"  ➤ Symbol: {symbol}")

# Total symbols checked and mismatched
total_mismatched = len(mismatches)
total_missing_crcs_in_xml = len(missing_crcs_in_xml)  # Only symbols found in symvers
total_missing_crcs_in_symvers = len(missing_crcs_in_symvers)  # Not found in both
total_successful_matches = matched_count

# Calculate total CRCs missing
total_missing_crcs = total_missing_crcs_in_xml + total_missing_crcs_in_symvers

# Ensure the summary adds up correctly
assert total_checked == (total_successful_matches + total_mismatched + total_missing_crcs_in_xml + total_missing_crcs_in_symvers), "The totals do not match!"

# Print summary with improved alignment
print("\nSummary:")
label_width = 45  # Width for labels
value_width = 5   # Width for values
print(f"{'Total Symbols Checked:':<{label_width}} {total_checked:>{value_width}}")
print(f"{'Total Successfully Matched CRCs:':<{label_width}} {total_successful_matches:>{value_width}}")
print(f"{'Total Mismatched Symbols:':<{label_width}} {total_mismatched:>{value_width}}")
print()
print(f"{'Total CRCs Missing:':<{label_width}} {total_missing_crcs:>{value_width}}")
print(f"{'Missing CRCs Found In Symvers:':<{label_width}} {total_missing_crcs_in_xml:>{value_width}}")
print(f"{'Missing CRCs Not Found In Symvers:':<{label_width}} {total_missing_crcs_in_symvers:>{value_width}}")

# Exit if there are CRC Mismatches
if mismatches:
    print()  # Print a newline before exiting
    sys.exit("Exiting Due To CRC Mismatches")