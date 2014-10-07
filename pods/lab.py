# Copyright 2014 Open Data Science Initiative and other authors. See AUTHORS.txt
# Licensed under the BSD 3-clause license (see LICENSE.txt)


import pandas as pd
import urlparse
import os
from config import *
import pickle
import pandas as pd
import pickle
import os
import numpy as np

gdata_available=True
try:
    import gdata.docs.client
    import gdata.spreadsheet.service # Requires python-gdata on Ubuntu
    import pods.google as gl
except ImportError:
    gdata_available=False

class_dir = os.path.expanduser(os.path.expandvars(config.get('class info', 'dir')))

if gdata_available:
    class distributor():
        """
        Class for interchanging information between google spreadsheets and pandas data frames. The class manages a spreadsheet.

        :param spreadsheet_key: the google key of the spreadsheet to open (default is None which creates a new spreadsheet).
        :param worksheet_name: the worksheet in the spreadsheet to work with (default 'Sheet1')
        :param title: the title of the spreadsheet (used if the spreadsheet is created for the first time)
        :param column_indent: the column indent to use in the spreadsheet.
        :type column_indent: int
        :param gd_client: the google spreadsheet service client to use (default is NOne which performs a programmatic login)
        :param docs_client: the google docs login client (default is none which causes a new client login)

        """
        def __init__(self, spreadsheet_title='Google Spreadsheet', keys_file=None, class_file=None, user_sep=','):
            self.spreadsheet_title = spreadsheet_title
            if keys_file is None:
                keys_file = 'spreadsheet_keys.pickle'
            if class_file is None:
                class_file = 'class_list.csv'
            self.class_file=os.path.join(class_dir, class_file)
            self.users = pd.read_csv(self.class_file, sep=user_sep)

            # load spreadsheet keys if they exist.
            if keys_file is None:
                self.keys_file=os.path.join(class_dir, 'spreadsheet_keys.pickle')
            else:
                self.keys_file=os.path.join(class_dir, keys_file)
                
            if os.path.exists(self.keys_file):
                self.sheet_keys = pickle.load(open(self.keys_file, "rb"))
            else:
                self.sheet_keys = {}


        def _get_name(self, user):
            """Get the name of a user with a given email."""
            ind = user==self.users.Email
            if ind.sum()==1:
                ind_val = self.users[ind].index[0]
                user_series = self.users.loc[ind_val]
                if 'name' in user_series:
                    return user_series.name
                elif 'Name' in user_series:
                    return user_series.Name
                elif 'Forename' in user_series:
                    if 'Surname' in user_series:
                        return user_series.Forename + ' ' + user_series.Surname
            else:
                return None

        def _get_sheet(self, user):
            """Get or create a sheet corresponding to a user."""
            # check if we've already got a spreadsheet for this user, otherwise create one.

            if user in self.sheet_keys:
                sheet = gl.sheet(spreadsheet_key=self.sheet_keys[user])
            else:
                name = self._get_name(user)
                title = self.spreadsheet_title
                if name is not None:
                    title += ' ' + name
                sheet = gl.sheet(title=title)
                self.sheet_keys[user] = sheet._key
                pickle.dump(self.sheet_keys, open(self.keys_file, "wb" ))
            return sheet

        def write_body(self, data_frame, header=2, function=None):
            """Write body of data to the users' directories."""
            for user in self.users.Email:
                if function is not None:
                    udata = function(data_frame)
                else:
                    udata = data_frame
                sheet = self._get_sheet(user)
                # Write the film data to the user's spreadsheet.
                sheet.write_body(udata, header=header)

        def write_comment(self, comment, row=1, column=1):
            """Write comments to the users' spreadsheets."""
            for user in self.users.Email:
                sheet = self._get_sheet(user)
                # Write the film data to the user's spreadsheet.
                sheet.write_comment(comment, row, column)

        def write_headers(self, data_frame, header=None):
            """Write comments to the users' spreadsheets."""
            for user in self.users.Email:
                sheet = self._get_sheet(user)
                # Write the film data to the user's spreadsheet.
                if header is None:
                    sheet.write_headers(data_frame)
                else:
                    sheet.write_headers(data_frame, header)
                
        def share(self, share_type='writer', send_notifications=False):
            """
            Share a document with a given list of users.
            """
            # share a document with the given list of users.
            for user in self.users.Email:
                sheet = self._get_sheet(user)
                sheet.share([user], share_type, send_notifications)

        def share_delete(self):
            """
            Remove sharing from all the class.
            """
            for user in self.users.Email:
                sheet = self._get_sheet(user)
                sheet.share_delete(user)

        def share_modify(self, share_type='reader', send_notifications=False):
            """
            :param user: email of the user to update.
            :type user: string
            :param share_type: type of sharing for the given user, type options are 'reader', 'writer', 'owner'
            :type user: string
            :param send_notifications: 
            """
            if share_type not in ['writer', 'reader', 'owner']:
                raise ValueError("Share type should be 'writer', 'reader' or 'owner'")
            for user in self.users.Email:
                sheet = self._get_sheet(user)
                sheet.share_modify(user, share_type, send_notifications)


        def write(self, data_frame, header=None, comment=None, function=None):
            """
            Write a pandas data frame to a google document. This function will overwrite existing cells, but will not clear them first.

            :param data_frame: the data frame to write.
            :type data_frame: pandas.DataFrame
            :param header: number of header rows in the document.
            :type header: int
            :param comment: a comment to make at the top of the document (requres header>1
            :type comment: str
            """
            for user in self.users.Email:
                if function is not None:
                    udata = function(data_frame)
                else:
                    udata = data_frame
                sheet = self._get_sheet(user)
                # Write the film data to the user's spreadsheet.
                sheet.write(udata, header=header, comment=comment)

        def update(self, data_frame, columns=None, header=1, comment=None, overwrite=True):
            """
            Update a google document with a given data frame. The
            update function assumes that the columns of the data_frame and
            the google document match, and that an index in either the
            google document or the local data_frame identifies one row
            uniquely. If columns is provided as a list then only the
            listed columns are updated.

            **Notes**

            :data_frame : data frame to update the spreadsheet with.
            :type data_frame: pandas.DataFrame
            :param columns: which columns are updated in the spreadsheet (by default all columns are updated)
            :type columns: list
            :param hearder_rows: how many rows are in the header (including the column headers). By default there is 1 row. 
            :type header: int
            :param comment: comment to place in the top row of the header (requires header>1)
            :type comment: str
            :rtype: pandas.DataFrame

            .. Note:: Returns the data frame that was found in the spreadsheet.

            """
            for user in self.users.Email:
                sheet = self._get_sheet(user)
                if function is not None:
                    udata = function(data_frame)
                else:
                    udata = data_frame
                sheet.update(udata, columns, header, comment, overwrite)


        def read(self, names=None, header=1, na_values=[], read_values=False, dtype={}, usecols=None):
            """
            Read in information from distributed Google documents storing entries. Fields present are defined in 'names'

            :param names: list of names to give to the columns (in case they aren't present in the spreadsheet). Default None (for None, the column headers are read from the spreadsheet.
            :type names: list
            :param header: number of rows to use as header (default is 1).
            :type header: int
            :param na_values: additional list containing entry types that are to be considered to be missing data (default is empty list).
            :type na_values: list
            :param read_values: whether to read values rather than the formulae in the spreadsheet (default is False).
            :type read_values: bool
            :param dtype: Type name or dict of column -> type Data type for data or columns. E.g. {'a': np.float64, 'b': np.int32}
            :type dtype: dictonary
            :param usecols: return a subset of the columns.
            :type usecols: list
            :return: a dictionary containing the results from each spreadsheet.
            :rtype: dict
            """
            data = {}
            for user in self.users.Email:
                sheet = self._get_sheet(user)
                data[user] = sheet.read(names, header, na_values, read_values, dtype, usecols)
            return data
