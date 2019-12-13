Value prefix ([\w\d\.]+\/\d{1,2})
Value protocol (\w+)
Value distance (\d+)
Value metric (\d+)
Value List next_hop ((?:[\d\.]+){3}\d{1,3}|self|Direct)
Value outgoing_interface ([\w\d\s]+)
Value age (\w+)

Start
  ^Routing entry\s(for\s)?${prefix}(\sis\s)?${next_hop}?
  ^\s*Known via \"${protocol}([\d\s]+)?\", distance ${distance}, metric ${metric}
  ^\s*Last update ${age} ago
  ^\s+(\*\s)?(via\s)?${next_hop},?( via )?${outgoing_interface}?
  ^$$
  ^$$ -> Next.Record
