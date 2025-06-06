from ccx_runner.gui.campbell_analysis import ComplexModalParser

if __name__ == "__main__":
    with open("./testfiles/simstep_50.0_0.dat", "r") as file:
        dat_file = file.read()

    parser = ComplexModalParser(dat_file)
    print(parser.data)
