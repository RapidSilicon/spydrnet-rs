from collections import deque, OrderedDict
from spydrnet.ir.port import Port


class Composer:

    def __init__(self):
        self.file = None
        self.direction_string_map = dict()
        self.direction_string_map[Port.Direction.IN] = "input"
        self.direction_string_map[Port.Direction.OUT] = "output"
        self.direction_string_map[Port.Direction.INOUT] = "inout"
        self.direction_string_map[Port.Direction.UNDEFINED] = "/* undefined port direction */ inout"

    def run(self, ir, file_out = "out.v"):
        self._open_file(file_out)
        self._compose(ir)
        

    def _open_file(self, file_name):
        f = open(file_name, "w")
        self.file = f

    def _compose(self, netlist):
        self._write_header(netlist)
        instance = netlist.top_instance
        if instance is not None:
            self._write_from_top(instance)
        
    def _write_header(self, netlist):
        self.file.write("////////////////////////////////////////\n")
        self.file.write("//File generated by SpyDrNet\n")
        if netlist.name is not None:
            self.file.write("//Netlist: " + netlist.name + "\n")
        self.file.write("////////////////////////////////////////\n")
        if netlist.top_instance is None:
            print("WARNING: Netlist has no top instance. Empty file written")
            self.file.write("//top instance is none.\n")

    def _write_from_top(self, instance):
        written = set()
        to_write = deque()
        to_write.append(instance.reference)
        self.file.write('(* STRUCTURAL_NETLIST = "yes" *)\n')
        while(len(to_write) != 0):
            definition = to_write.popleft()
            if definition in written:
                continue
            written.add(definition)
            for c in definition.children:
                if c.reference not in written:
                    to_write.append(c.reference)
            # print("writing definition", definition.name)
            self._write_definition_single(definition)

    def _write_definition_single(self, definition):
        if "VERILOG.primative" in definition and definition["VERILOG.primative"] == True:
            return #no need to write the primative definition out, vivado already knows.
        self.file.write("module ")
        self._write_escapable_name(definition.name)
        self.file.write("\n")
        self._write_ports(definition)

        for c in definition.cables:
            self._write_cable(c)

        for i in definition.children:
            self._write_instanciation(i)
        
        for c in definition.cables:
            self._write_assignments(c)

        self.file.write("endmodule\n")

    def _write_assignments(self,cable):
        for k,v in cable.data.items():
            k = k.split(".")
            if k[0] == "VERILOG" and k[1] == "assignment" and v == "true":
                self.file.write("assign ")
                self._write_escapable_name(k[2])
                self.file.write(" ;\n")

    def _write_ports(self, definition):
        self.file.write("(\n    ")
        first = True
        port_to_rename = dict()
        in_rename = set()
        for p in definition.ports:
            highest_position = 0
            rename_members = OrderedDict()
            for k,v in p.data.items():
                k = k.split(".")
                if k[0] == "VERILOG" and k[1] == "port_rename":
                    rename = True
                    position = k[2]
                    if int(position) > highest_position:
                        highest_position = int(position)
                    rename_members[int(position)] = v
                elif k[0] == "VERILOG" and k[1] == "port_rename_member" and v == "true":
                    in_rename.add(p)
                    continue

            if len(rename_members.keys()) == 0:
                pass
            elif len(rename_members.keys()) == 1:
                port_to_rename[p] = rename_members[0]
            else:
                rename_str = "{ "
                for i in range(highest_position+1):
                    if i == 0:
                        pass
                    else:
                        rename_str += " , "
                    rename_str += rename_members[i]
                    
                rename_str += " } "
                port_to_rename[p] = rename_str
                    


                    
        for p in definition.ports:
            if p in in_rename:
                continue
              
            if first:
                #self.file.write(p.name)    
                first = False
            else:
                self.file.write(",\n    ")
                #self.file.write(p.name)
            if p in port_to_rename:
                self.file.write(".")
                self._write_escapable_name(p.name)
                self.file.write("(")
                self.file.write(port_to_rename[p])
                self.file.write(")")
            else:
                self._write_escapable_name(p.name)
        self.file.write("\n);\n")
        for p in definition.ports:
            if p in port_to_rename:
                continue
            
            self.file.write(self.direction_string_map[p.direction])
            self.file.write(" ")
            if not p.is_scalar:
                if p.is_downto:
                    left = p.lower_index + len(p.pins) - 1
                    right = p.lower_index
                else:
                    left = p.lower_index
                    right = p.lower_index + len(p.pins) - 1
                self.file.write("["+str(left)+":"+str(right)+"]")
            #self.file.write(p.name)
            self._write_escapable_name(p.name)
            self.file.write(";\n")

    def _write_cable(self, cable):
        self.file.write("wire ")
        if not cable.is_scalar:
            if cable.is_downto:
                left = cable.lower_index + len(cable.wires) - 1
                right = cable.lower_index
            else:
                left = cable.lower_index
                right = cable.lower_index + len(cable.wires) - 1
            self.file.write("["+str(left)+":"+str(right)+"]")
        #self.file.write(cable.name)
        self._write_escapable_name(cable.name)
        self.file.write(";\n")

    def _write_instanciation(self, instance):
        parameters = dict()
        for k, v in instance.data.items():
            if "VERILOG.star." == k[:13]:
                if v is not None:
                    self.file.write("(* " + k[13:] + " = " + v + " *)\n")
                else:
                    self.file.write("(*" + k[13:] + "*)\n")

            if "VERILOG.parameters." == k[:19]:
                parameters[k[19:]] = v
        #self.file.write(instance.reference.name)
        self._write_escapable_name(instance.reference.name)
        
        if len(parameters.items()) != 0:
            self.file.write("#(\n")
            first = True
            for k,v in parameters.items():
                if first:
                    first = False
                else:
                    self.file.write(",\n")
                self.file.write("." + k + "(" + v + ")")
            self.file.write(")\n")
        self.file.write(" ")
        #self.file.write(instance.name)
        self._write_escapable_name(instance.name)
        self.file.write("\n(\n")
        first = True
        port_pin_dict = dict()
        for port in instance.reference.ports:
            port_pin_dict[port] = []
        for pin in instance.pins:
            port_pin_dict[pin.inner_pin.port].append(pin)
        for p in instance.reference.ports:
            cable_name = self._write_port_wires(port_pin_dict[p])
            if cable_name is not None:
                if first:
                    first = False
                #TODO: self.file.write(cableconnected to port name)
                else:
                    self.file.write(",\n")
                self.file.write("    .")
                self._write_escapable_name(p.name)
                self.file.write("(")
                #self._write_port_wires(port_pin_dict[p])
                #self.file.write(cable_name)
                self._write_escapable_name(cable_name)
                self.file.write(")")
        self.file.write("\n);\n")
        

    def _write_port_wires(self, pins):
        string_to_write = ""
        wires = []
        for pin in pins:
            if pin.wire is not None:
                wires.append(pin.wire)

        if len(wires) == 0:
            return None

        cable = None
        count = 0
        c_wires = []
        for w in wires:
            
            if cable != w.cable:
                if cable != None:
                    string_to_write = self._indicies_from_wires(cable, c_wires, string_to_write)
                    if string_to_write[0] != "{":
                        string_to_write = "{" + string_to_write
                    string_to_write = string_to_write + " , " + w.cable.name
                else:
                    string_to_write = w.cable.name
                cable = w.cable
                count = 0
                c_wires = []
            count += 1
            c_wires.append(w)
        
        string_to_write = self._indicies_from_wires(cable, c_wires, string_to_write)
        if string_to_write[0] == "{":
            string_to_write += " }"

        return string_to_write
        
    def _get_wire_index(self, cable, wire):
        i = 0
        val = None
        for w in cable.wires:
            if wire == w:
                val = i
                break
            i += 1
        return val
        


    def _indicies_from_wires(self, cable, wires, string_to_write):
        low = None
        high = None
        for w in wires:
            idx = self._get_wire_index(cable, w)
            if (low is None) or idx < low:
                low = idx
            if (high is None) or idx > high:
                high = idx
        #if low == cable.lower_index and high == cable.lower_index + len(cable.wires) - 1:
        if high - low == len(cable.wires) -1:
            pass
        elif low == high:
            string_to_write += " [" + str(low + cable.lower_index) + "]"
        else:
            string_to_write += " [" + str(low + cable.lower_index) + ":" + str(high + cable.lower_index) + "]"
        return string_to_write

        # pin_cable = pin.wire.cable
        # if len(pins) == len(pin_cable.wires):
        #     #self.file.write(pin_cable.name)
        #     string_to_write += pin_cable.name
        # elif len(pins) == 1:
        #     if len(pin_cable.wires) == 1:
        #         #self.file.write(pin_cable.name)
        #         string_to_write += pin_cable.name
        #     else:
        #         i = 0
        #         for w in pin_cable.wires:
        #             if w == pin.wire:
        #                 break
        #             i += 1
        #         #self.file.write(pin_cable.name)
        #         #self.file.write("[" + str(i) + "]")
        #         string_to_write += pin_cable.name
        #         string_to_write +="[" + str(i) + "]"
        # else:
        #     left_pin = pins[0]
        #     right_pin = pins[len(pins)-1]
        #     i = 0
        #     left_wire_index = None
        #     right_wire_index = None
        #     for w in pin_cable.wires:
        #         if w == left_pin.wire:
        #             left_wire_index = i
        #         if w == right_pin.wire:
        #             right_wire_index = i
        #         i += 1
        #         if left_wire_index == None and right_wire_index == None:
        #             break
        #     #self.file.write(pin_cable.name)
        #     #self.file.write("[" + str(left_wire_index) + ":" + str(right_wire_index) + "]")
        #     string_to_write += pin_cable.name
        #     string_to_write += "[" + str(left_wire_index) + ":" + str(right_wire_index) + "]"
        # return string_to_write

    def _write_escapable_name(self, str_in):
        if str_in[0] == "\\":
            self.file.write(str_in + " ")
        else:
            self.file.write(str_in)