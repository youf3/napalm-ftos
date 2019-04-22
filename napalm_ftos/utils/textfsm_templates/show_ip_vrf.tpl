#VRF-Name                         VRF-ID Interfaces
#default                          0       Fo 1/51,1/52,1/54,
#                                          Ma 1/1,
#                                          Nu 0,
#                                          Vl 1,202,999,2000,3301
#admin                            101     Vl 101,3101
#manta                            103     Vl 1001,3201
Value VRF_NAME ([a-f0-9\.:]+)
Value VRF_ID (\d+)

Start
  ^(\*)?\s+\d+.* -> Continue.Record
  ^${VRF_NAME}\s+${VRF_ID}.* -> Record
