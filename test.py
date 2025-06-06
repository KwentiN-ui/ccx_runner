from ccx_runner.gui.campbell_analysis import ComplexModalParseResult

if __name__ == "__main__":
    with open("./testfiles/simstep_6400.0_18.dat", "r") as file:
        dat_file = file.read()

    parser = ComplexModalParseResult(dat_file, 6400)
