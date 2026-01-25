import pprint as pprint
import matplotlib.pyplot as plt
import networkx as nx
import random
import create_use_resources as res



""" this file would contain all the functions to create a random playing board of europe given number of players.
    number of players it will randomly choose the right number of contiguous colored ares
    and generate the board graph the starting player order and deal the cards.

    the output is a graph in dictionary form with colors city and cost

    e.g.  {('red', 'Marseille'): {('red', 'Bordeaux'): 12, ('red', 'Lyon'): 8, ('red', 'Barcelona'): 11}}

    if you install networkx and uncomment the last few lines you can draw the graph

     """


def generate_color_graph(game_colors):
    """a list of colors and edges   returns a graph of connected colors"""

    def make_link(G, node1, node2):
        if node1 not in G:
            G[node1] = {}
        (G[node1])[node2] = 1
        if node2 not in G:
            G[node2] = {}
        (G[node2])[node1] = 1
        return G

    G = {}
    for (x,y) in game_colors:
        make_link(G,x,y)
    return G



def random_choose_play_area(number_of_players, color_graph):
    """input number of players and a graph of area colors of the continent and returns a randomly chosen color list based on the
    dictionary of players per areas"""

    areas_per_player_dict = {2:3, 3:3, 4:4, 5:5, 6:5}
    path_lists = []
    for k in color_graph.keys():
        for ki in color_graph[k].keys():
            for kj in color_graph[ki].keys():
                if set([k, ki, kj]) not in path_lists:
                    path_lists.append(set([k, ki, kj]))
                for kk in color_graph[kj].keys():
                    if set([k, ki, kj, kk]) not in path_lists:
                        path_lists.append(set([k, ki, kj, kk]))
                        for kl in color_graph[kk].keys():
                            if set([k, ki, kj, kk, kl]) not in path_lists:
                                path_lists.append(set([k, ki, kj, kk, kl]))
    area_five = []
    area_three = []
    area_four = []


    for s in path_lists:
        if len(s) == 3:
            area_three.append(list(s))
        elif len(s) == 4:
            area_four.append(list(s))
        elif len(s) == 5:
            area_five.append(list(s))
    if areas_per_player_dict[number_of_players] == 3:
        return random.choice(area_three)
    elif areas_per_player_dict[number_of_players]== 4:
        return random.choice(area_four)
    elif areas_per_player_dict[number_of_players]== 5:
        return random.choice(area_five)



# list of colors, nodes, edges and costs
europe = [(('red', 'Lisboa'), ('red', 'Madrid'), 13), (('red', 'Madrid'), ('red', 'Bordeaux'), 16), (('red', 'Barcelona'), ('red', 'Marseille'), 11), (('red', 'Barcelona'), ('red', 'Madrid'), 14),
          (('red', 'Barcelona'), ('red', 'Bordeaux'), 15), (('red', 'Marseille'), ('red', 'Bordeaux'), 12), (('red', 'Bordeaux'), ('red', 'Paris'), 12), (('red', 'Marseille'), ('red', 'Lyon'), 8),
          (('red', 'Bordeaux'), ('red', 'Lyon'), 12), (('purple', 'London'), ('red', 'Paris'), 16), (('red', 'Paris'), ('red', 'Lyon'), 11), (('red', 'Paris'), ('purple', 'Rhein-Ruhr'), 10),
          (('red', 'Paris'), ('purple', 'Rhein-Ruhr'), 10), (('red', 'Paris'), ('purple', 'Vlaanderen'), 7), (('purple', 'Randstad'), ('purple', 'London'), 18), (('purple', 'Rhein-Ruhr'), ('purple', 'Vlaanderen'), 4),
          (('purple', 'Vlaanderen'), ('purple', 'London'), 15), (('purple', 'London'), ('purple', 'Birmingham'), 4), (('purple', 'Birmingham'), ('purple', 'Glasgow'), 13), (('purple', 'Birmingham'), ('purple', 'Dublin'), 15),
          (('purple', 'Dublin'), ('purple', 'Glasgow'), 17), (('purple', 'Randstad'), ('purple', 'Vlaanderen'), 4), (('red', 'Paris'), ('brown', 'Stuttgart'), 14), (('purple', 'Randstad'), ('brown', 'Bremen'), 8),
          (('purple', 'Vlaanderen'), ('brown', 'Bremen'), 10), (('purple', 'Vlaanderen'), ('brown', 'Rhein-Main'), 6), (('purple', 'Rhein-Ruhr'), ('brown', 'Rhein-Main'), 3),
          (('purple', 'Rhein-Ruhr'), ('brown', 'Stuttgart'), 5), (('brown', 'Rhein-Main'), ('brown', 'Stuttgart'), 3), (('brown', 'Rhein-Main'), ('brown', 'Berlin'), 10), (('brown', 'Rhein-Main'), ('brown', 'Praha'), 10),
          (('brown', 'Rhein-Main'), ('brown', 'Munchen'), 6), (('brown', 'Stuttgart'), ('brown', 'Munchen'), 4), (('brown', 'Berlin'), ('brown', 'Bremen'), 6), (('brwon', 'Praha'), ('brown', 'Munchen'), 8),
          (('brown', 'Praha'), ('brown', 'Katowice'), 8), (('brown', 'Praha'), ('brown', 'Berlin'), 7), (('blue', 'Beograd'), ('blue', 'Tirane'), 15), (('blue', 'Beograd'), ('blue', 'Sofia'), 11),
          (('blue', 'Sofia'), ('blue', 'Tirane'), 13), (('blue', 'Sofia'), ('blue', 'Istanbul'), 13), (('blue', 'Sofia'), ('blue', 'Athina'), 17), (('blue', 'Tirane'), ('blue', 'Athina'), 16),
          (('blue', 'Istanbul'), ('blue', 'Izmir'), 8), (('blue', 'Istanbul'), ('blue', 'Ankara'), 9), (('blue', 'Izmir'), ('blue', 'Ankara'), 10), (('blue', 'Beograd'), ('green', 'Bucuresti'), 12),
          (('blue', 'Sofia'), ('green', 'Bucuresti'), 9), (('blue', 'Istanbul'), ('green', 'Bucuresti'), 13), (('blue', 'Beograd'), ('yellow', 'Budapest'), 10), (('brown', 'Rhein-Main'), ('brown', 'Stuttgart'), 3),
          (('brown', 'Rhein-Main'), ('brown', 'Bremen'), 9), (('brown', 'Rhein-Main'), ('brown', 'Berlin'), 10), (('brown', 'Rhein-Main'), ('brown', 'Praha'), 10), (('brown', 'Rhein-Main'), ('brown', 'Munchen'), 6),
          (('brown', 'Rhein-Main'), ('purple', 'Rhein-Ruhr'), 3), (('brown', 'Rhein-Main'), ('purple', 'Vlaanderen'), 6), (('brown', 'Bremen'), ('purple', 'Vlaanderen'), 10), (('green', 'Kyjiv'), ('brown', 'Katowice'), 18),
          (('green', 'Warszawa'), ('brown', 'Katowice'), 5), (('green', 'Warszawa'), ('brown', 'Praha'), 11), (('green', 'Warszawa'), ('brown', 'Berlin'), 11), (('green', 'Kyjiv'), ('green', 'Warszawa'), 14),
          (('green', 'Kyjiv'), ('green', 'Minsk'), 10), (('green', 'Kyjiv'), ('green', 'Kharkiv'), 9), (('green', 'Kyjiv'), ('green', 'Odessa'), 9), (('green', 'Kharkiv'), ('green', 'Odessa'), 13),
          (('green', 'Kharkiv'), ('green', 'Moskwa'), 15), (('green', 'Warszawa'), ('green', 'Minsk'), 10), (('green', 'Warszawa'), ('orange', 'Kobenhavn'), 25), (('green', 'Kyjiv'), ('yellow', 'Budapest'), 21),
          (('orange', 'Kobenhavn'), ('brown', 'Bremen'), 12), (('orange', 'Kobenhavn'), ('brown', 'Berlin'), 15), (('orange', 'Riga'), ('green', 'Warszawa'), 12), (('orange', 'Riga'), ('green', 'Minsk'), 8),
          (('orange', 'Riga'), ('green', 'Moskwa'), 18), (('orange', 'Kobenhavn'), ('green', 'Warszawa'), 25), (('orange', 'Riga'), ('orange', 'Sankt-Peterburg'), 13), (('orange', 'Riga'), ('orange', 'Tallinn'), 7),
          (('orange', 'Kobenhavn'), ('orange', 'Stockholm'), 18), (('orange', 'Kobenhavn'), ('orange', 'Oslo'), 17), (('orange', 'Stockholm'), ('orange', 'Oslo'), 13), (('orange', 'Stockholm'), ('orange', 'Helsinki'), 21),
          (('orange', 'Sankt-Peterburg'), ('orange', 'Tallinn'), 9), (('orange', 'Sankt-Peterburg'), ('orange', 'Helsinki'), 11), (('purple', 'Randstad'), ('brown', 'Bremen'), 8), (('yellow', 'Napoli'), ('blue', 'Tirane'), 25),
          (('yellow', 'Napoli'), ('blue', 'Beograd'), 18), (('yellow', 'Zagreb'), ('blue', 'Beograd'), 9), (('yellow', 'Milano'), ('brown', 'Munchen'), 16), (('yellow', 'Zurich'), ('brown', 'Stuttgart'), 5),
          (('yellow', 'Zurich'), ('brown', 'Munchen'), 8), (('yellow', 'Zagreb'), ('brown', 'Munchen'), 14), (('yellow', 'Milano'), ('red', 'Marseille'), 13), (('yellow', 'Milano'), ('red', 'Lyon'), 11),
          (('yellow', 'Zurich'), ('red', 'Lyon'), 14), (('yellow', 'Zurich'), ('red', 'Paris'), 14), (('yellow', 'Milano'), ('yellow', 'Zurich'), 11), (('yellow', 'Milano'), ('yellow', 'Roma'), 19),
          (('yellow', 'Milano'), ('yellow', 'Zagreb'), 17), (('yellow', 'Napoli'), ('yellow', 'Roma'), 7), (('yellow', 'Zagreb'), ('yellow', 'Wien'), 8), (('yellow', 'Zagreb'), ('yellow', 'Budapest'), 7),
          (('yellow', 'Budapest'), ('brown', 'Katowice'), 11), (('yellow', 'Budapest'), ('green', 'Odessa'), 25), (('yellow', 'Budapest'), ('green', 'Bucuresti'), 16), (('yellow', 'Budapest'), ('yellow', 'Wien'), 5),
          (('brown', 'Berlin'), ('brown', 'Praha'), 7), (('brown', 'Bremen'), ('brown', 'Berlin'), 6), (('brown', 'Katowice'), ('yellow', 'Budapest'), 11),
          (('brown', 'Katowice'), ('brown', 'Praha'), 8), (('brown', 'Katowice'), ('yellow', 'Wien'), 8), (('brown', 'Munchen'), ('brown', 'Stuttgart'), 4),
          (('brown', 'Praha'), ('yellow', 'Wien'), 7), (('brown', 'Stuttgart'), ('brown', 'Munchen'), 4), (('brown', 'Stuttgart'), ('purple', 'Rhein-Ruhr'), 5),
          (('brown', 'Stuttgart'), ('red', 'Paris'), 14), (('green', 'Bucuresti'), ('yellow', 'Budapest'), 16), (('green', 'Bucuresti'), ('green', 'Odessa'), 10),
          (('green', 'Moskwa'), ('orange', 'Sankt-Peterburg'), 14), (('green', 'Moskwa'), ('green', 'Minsk'), 14), (('green', 'Odessa'), ('green', 'Bucuresti'), 10),
          (('orange', 'Sankt-Peterburg'), ('green', 'Moskwa'), 14), (('yellow', 'Wien'), ('brown', 'Munchen'), 9), (('green', 'Minsk'), ('green', 'Kharkiv'), 16),
          (('brown', 'Munchen'), ('yellow', 'Wien'), 9), (('brown', 'Praha'), ('brown', 'Munchen'), 8)]





def create_game_board(continent, color_list):
    """input list of all the countries in the continent and a list of the colors base on number of players returns eligible nodes"""
    game_board = []
    for city in continent:
        if city[0][0] in color_list and city [1][0] in color_list:
            game_board.append(city)
    return game_board




def generate_game_graph(game_board):
    """included countries list:  color, nodes, edges and costs  returns game_graph"""

    def make_link(G, node1, node2, cost):
        if node1 not in G:
            G[node1] = {}
        (G[node1])[node2] = cost
        if node2 not in G:
            G[node2] = {}
        (G[node2])[node1] = cost
        return G

    G = {}
    for (x,y,z) in game_board: make_link(G,x,y,z)
    return G




#europe areas need to be created
eur_areas = [('brown', 'red'), ('brown', 'purple'),  ('brown', 'yellow'),  ('brown', 'green'),  ('brown', 'orange'), ('purple', 'red'), ('red', 'yellow'), ('yellow', 'blue'), ('yellow', 'green'), ('blue', 'green'), ('orange', 'green')]

G=nx.Graph()
# explicitly set positions
pos={'Lisboa':(0,0),
     'Madrid':(0.4,0.5),
     'Paris':(0.75,3),
     'Lyon':(1.1,2.25),
     'Bordeaux':(0.3,2),
     'Barcelona':(1,0),
     'Marseille':(1,1),
     'Dublin':(0,4.5),
     'Glasgow':(0.2,6),
     'Birmingham':(0.4,5),
     'London':(0.5,4),
     'Randstad':(1.25,5.3),
     'Vlaanderen':(1.25,4.3),
     'Rhein-Ruhr':(1.4,3.4),
     'Bremen':(2,5.75),
     'Berlin': (3.8, 5.2),
     'Rhein-Main': (2.1, 4.5),
     'Stuttgart': (1.8, 2.8),
     'Munchen': (2.75, 3.5),
     'Praha': (4, 4.25),
     'Katowice': (4.75, 4.25),
     'Oslo': (4, 8),
     'Kobenhavn': (4, 6.5),
     'Stockholm': (5, 7.5),
     'Helsinki': (7, 8),
     'Tallinn': (6.5, 7.5),
     'Riga': (6.5, 6.5),
     'Sankt-Peterburg': (7.5, 7.5),
     'Minsk': (7, 6),
     'Moskwa': (8, 6),
     'Warszawa': (5, 5.5),
     'Kharkiv': (8, 4.5),
     'Kyjiv': (7, 4.5),
     'Budapest': (6.5, 3.5),
     'Odessa': (8, 3.75),
     'Bucuresti': (7.5, 3),
     'Istanbul': (7.5, 1),
     'Ankara': (8, 0.5),
     'Izmir': (7.5, 0),
     'Sofia': (7, 1.25),
     'Athina': (6.5, 0),
     'Tirane': (6, 0.5),
     'Wien': (5, 3),
     'Zurich': (2.25, 2.25),
     'Milano': (2.5, 1),
     'Zagreb': (4, 2),
     'Roma': (3, 0.5),
     'Napoli': (4.5, 0.5),
     'Beograd': (6.25, 2)}

def create_city_nodes(graph):
    """returns list of city nodes"""
    city_nodes = [a for a in graph.keys()]
    cities = [a[1] for a in city_nodes]
    return cities

def create_city_edges(graph):
    """returns a list of all edges"""
    city_edges = []
    city_nodes = [a for a in graph.keys()]
    for c in city_nodes:
        for e in graph[c]:
            city_edges.append((c[1], e[1]))
    return city_edges

def create_label_dict(city_nodes):
    """returns a dictionary of city: city key value pair"""
    label_dict = {}
    for c in city_nodes:
        label_dict[c]=c
    return label_dict

def create_edge_labels(game_board):
    """returns a dictionary of edges and costs"""
    edge_labels = {}
    for edge in game_board:
        edge_labels[(edge[0][1],edge[1][1])] = edge[2]
    return edge_labels

def starting_player_order(number_of_players):
    start_order = list(range(1,number_of_players+1))
    random.shuffle(start_order)
    return start_order

def market_setup(number_of_players):

    """returns 2 lists, the first 9 dark cards for the starting marketplace and the rest of the deck ready for play  the stage 3 card is 99 'stage three'"""

    cards = [['44', 'green', '0', '6'], ['36', 'green', '0', '5'], ['31', 'green', '0', '4'], ['28', 'green', '0', '3'], ['24', 'green', '0', '3'], ['17', 'green', '0', '2'], ['11', 'green', '0', '1'],
             ['46', 'gas', '2', '7'], ['39', 'gas', '2', '6'], ['34', 'gas', '3', '6'], ['26', 'gas', '1', '4'], ['19', 'gas', '1', '3'], ['16', 'gas', '2', '3'], ['14', 'gas', '1', '2'], ['5', 'gas', '2', '1'],
             ['40', 'coal', '2', '6'], ['33', 'coal', '3', '6'], ['29', 'coal', '2', '5'], ['27', 'coal', '1', '4'], ['25', 'coal', '2', '5'], ['20', 'coal', '3', '4'], ['15', 'coal', '1', '2'], ['12', 'coal', '2', '2'],
             ['9', 'coal', '3', '2'], ['7', 'coal', '1', '1'], ['4', 'coal', '2', '1'], ['3', 'coal', '2', '1'], ['42', 'oil', '2', '6'], ['38', 'oil', '3', '6'], ['30', 'oil', '2', '5'], ['23', 'oil', '2', '4'],
             ['18', 'oil', '2', '3'], ['10', 'oil', '2', '2'], ['6', 'oil', '1', '1'], ['50', 'nuclear', '2', '7'], ['37', 'nuclear', '2', '6'], ['32', 'nuclear', '2', '5'], ['21', 'nuclear', '1', '3'],
             ['13', 'nuclear', '1', '2'], ['35', 'oil&gas', '2', '5'], ['22', 'oil&gas', '3', '5'], ['8', 'oil&gas', '2', '3']]

    for c in cards:
        for i in range(len(c)):
            if len(c[i])< 3:
                c[i] = int(c[i])

    for c in cards:
        if c[0] < 16:
            c.append('dark')
        else:
            c.append('light')

    dark_cards = []
    light_cards = []

    for c in cards:
        if c[0] < 16:
            dark_cards.append(c)
        else:
            light_cards.append(c)

    random.shuffle(dark_cards)
    random.shuffle(light_cards)

    if number_of_players == 3:
        dark_cards = dark_cards[:-2]
        light_cards = light_cards[:-6]

    elif number_of_players == 4:
        dark_cards = dark_cards[:-1]
        light_cards = light_cards[:-3]


    first_nine_cards = dark_cards[:9]
    rest_of_dark_cards = dark_cards[9:]

    remaining_deck = rest_of_dark_cards + light_cards
    random.shuffle(remaining_deck)
    remaining_deck.append([99, 'stage three', 0, 0, 'light'])

    return first_nine_cards, remaining_deck

def occupied_city_dict(list_of_cities):
    occ_city_dict = {}
    for c in list_of_cities:
        occ_city_dict[c] = [10,15,20]
    return occ_city_dict

#*****************************************************************


color_graph = generate_color_graph(eur_areas)

number_players = 4


#create variables for generating the graph
the_random_play_areas = random_choose_play_area(number_players, color_graph)
#print(the_random_play_areas)
game_board = create_game_board(europe, the_random_play_areas)

#create the final graph (dictionary)
the_game_graph = generate_game_graph(game_board)

pp = pprint.PrettyPrinter(indent=4)
pp.pprint(the_game_graph)


#create variables for drowing out the graph
city_nodes = create_city_nodes(the_game_graph)
city_edges = create_city_edges(the_game_graph)
label_dictionary = create_label_dict(city_nodes)
edge_labels = create_edge_labels(game_board)
#draw nodes and edges
nx.draw_networkx_nodes(G, pos, node_shape='None', nodelist=pos.keys(), node_color='w')
nx.draw_networkx_edges(G, pos, alpha=0.5,width=3, edgelist= city_edges, edge_color='0.85')
#draw lables on nodes and edges
nx.draw_networkx_labels(G, pos, labels=label_dictionary, font_color = 'green', font_size=12, font_family='sans-serif')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, label_pos=0.5)
#actually draw the graph  uncomment to save a png file to print
plt.axis('off')
#plt.savefig("europe.png") # save as png
#plt.show() # display


test_initial_market = market_setup(number_players)

print(test_initial_market[0])
print(test_initial_market[1])

total_supply_coal = 27
start_supply_coal = (2, 9)
total_supply_gas = 24
start_supply_gas = (3, 8)
total_supply_oil = 20
start_supply_oil = (3, 9)
total_supply_uranium = 12
start_supply_uranium = (8, 9)




coal_cl = [[1 ,[0 ,0 ,0 ,0]] ,[2 ,[0 ,0 ,0 ,0]] ,[3 ,[0 ,0 ,0 ,0]] ,[4 ,[0 ,0 ,0 ,0]] ,[5 ,[0 ,0 ,0 ,0]]
           ,[6, [0 ,0 ,0 ,0]] ,[7, [0 ,0]] ,[8, [0 ,0]] ,[9, [0 ,0]]]
gas_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], [5, [0, 0, 0, 0]]
    , [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
oil_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], [5, [0, 0, 0, 0]]
    , [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]
uranium_cl = [[1, [0, 0, 0, 0]], [2, [0, 0, 0, 0]], [3, [0, 0, 0, 0]], [4, [0, 0, 0, 0]], [5, [0, 0, 0, 0]]
    , [6, [0, 0, 0, 0]], [7, [0, 0]], [8, [0, 0]], [9, [0, 0]]]

coal = res.Resource(total_supply_coal, start_supply_coal, coal_cl, 'coal')
coal.initialize_supply()
gas = res.Resource(total_supply_gas, start_supply_gas, gas_cl, 'gas')
gas.initialize_supply()
oil = res.Resource(total_supply_oil, start_supply_oil, oil_cl, 'oil')
oil.initialize_supply()
uranium = res.Resource(total_supply_uranium, start_supply_uranium, uranium_cl, 'uranium')
uranium.initialize_supply()

print('total resource supply')
coal.show_supply()
gas.show_supply()
oil.show_supply()
uranium.show_supply()
print('starting resource board')
print('Coal:')
coal.show_board()
print('Gas:')
gas.show_board()
print('Oil:')
oil.show_board()
print('Uranium:')
uranium.show_board()

print(occupied_city_dict(city_nodes))