# from keras.utils import plot_model
# from keras.models import load_model
# model=load_model('TLCS\models\model_1\\trained_model.h5')
# plot_model(model, to_file='TLCS\models\model_1\model_structure.png', show_shapes=True, show_layer_names=True)

# import os
# import sys
# import traci

# # Đường dẫn đến thư mục SUMO
# if 'SUMO_HOME' in os.environ:
#     tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
#     sys.path.append(tools)
# else:
#     sys.exit("Vui lòng khai báo biến môi trường SUMO_HOME")

# # Cấu hình mô phỏng
# CONFIG_FILE = 'TLCS\intersection\sumo_config.sumocfg'  # Tệp cấu hình

# def run_simulation():
#     # Bắt đầu kết nối với SUMO
#     traci.start(["sumo-gui", "-c", CONFIG_FILE, '--delay', '10'])
#     step = 5000
#     try:
#         while step > 0:
#             traci.simulationStep()
#             vehicles=traci.vehicle.getIDList()
#             arrived=traci.simulation.getArrivedIDList()
#             if arrived != ():
#                 print(arrived)
#             # for vehicel in vehicles:
#             #     print(traci.vehicle.getlo)
#             step-=1
#     finally:
#         traci.close()

# if __name__ == "__main__":
    
#     run_simulation()

