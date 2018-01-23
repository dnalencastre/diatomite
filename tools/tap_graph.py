#!/usr/bin/env python2
"""
    Display graphs of values from Diatomite RF analyzer taps.
    Copyright (C) 2017 Duarte Alencastre

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
                    GNU AFFERO GENERAL PUBLIC LICENSE
                       Version 3, 19 November 2007
"""

import Gnuplot
import numpy
import argparse
import logging
from ast import literal_eval as make_tuple


def tap_graph_main(args):
    """Output the graphic"""

    g = Gnuplot.Gnuplot()
    graph_title = ''
    g.title("Log power FFT")

    g.xlabel("frequency")
    g.ylabel("DBm")

    while True:
        with open(args.input_file, 'r') as f_handle:
            for line in f_handle:

                # tap has trailin newlines
                if not line == '\n':
                    try:
                        date_time, bw, lf, hf, fft_values_raw = line.split(';')
                    except ValueError:
                        # got incomplete line, read next one
                        msg = 'Tap has incomplete line'
                        logging.warning(msg)
                    else:
                        fft_values = make_tuple(fft_values_raw.rstrip())
                        fft_values_len = len(fft_values)

                        low_freq = int(lf)
                        high_freq = int(hf)

                        freq_step = float((float(hf) - float(lf)) / fft_values_len)


                        x = numpy.arange(start=low_freq,
                                         stop=high_freq,
                                         step=freq_step,
                                         dtype='float_')

                        y_values = fft_values
                        x_values = x

#                         slice =
                        g.set_range('yrange', (-110, 0))
                        g('set format x "%.3s%c"')
#                         g.set_range('xrange', (89490000, 89510000))

                        d1 = Gnuplot.Data(x_values, y_values,
                                          title=graph_title, with_="lines")
                        term_width = 200
                        term_height = 40
                        term_set = ('set terminal dumb feed size {tw},'
                                    ' {th} aspect 2, 1').format(tw=term_width,
                                                                th=term_height)

                        g(term_set)
                        g.plot(d1)

                        print('lower freqyency :{lf}, upper frequency:{hf},'
                              ' Bucket size:{fs}').format(lf=low_freq,
                                                          hf=high_freq,
                                                          fs=freq_step)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Output graphics from Diatomite taps.')
    parser.add_argument('-f', '--file', help='specify input file',
                        dest='input_file', required=True)
    args = parser.parse_args()
    tap_graph_main(args)
