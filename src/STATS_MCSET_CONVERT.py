#/***********************************************************************
# * Licensed Materials - Property of IBM 
# *
# * IBM SPSS Products: Statistics Common
# *
# * (C) Copyright IBM Corp. 1989, 2014
# *
# * US Government Users Restricted Rights - Use, duplication or disclosure
# * restricted by GSA ADP Schedule Contract with IBM Corp. 
# ************************************************************************/

__author__ = "IBM SPSS, JKP"
__version__ = "1.0.1"

# history
# 07-26-2013  original version


import spss, spssaux
from extension import Template, Syntax, processcmd

helptext="""
Convert a multiple category set into a multiple dichotomy set.

STATS MCSETS CONVERT MCSET=mcset VARPREFIX=string SETNAME=setname.
/HELP

All fields are required.

Example:
STATS MCSET CONVERT MCSET = $mcset1 VARPREFIX=set1 SETNAME=$fromset1.

This procedure converts a multiple category set into a multiple dichotomy set.
It generates a dichotomous variable for each value found in the variables
that define the MC set and assigns the value labels, if any, taken from the
first variable in the set as the variable labels of the new variables.

You might want to do this in order to use the
STATS CATEGORY ORDER extension command for working with CTABLES.

Existing variables are overwritten, but if there is a type conflict,
an error will be generated.


MCSET is a multiple category set to convert to a multiple dichotomy set.


VARPREFIX specifies text that will be prepended to the names of the generated
names that form the output.  The generated names have the form
prefix_nn
where nn is a number and may overwrite an existing variable.

SETNAME is the name for the output multiple dichotomy set.

/HELP displays this text and does nothing else.
"""


import spss, spssaux, spssdata

def catvalues(mcset, varprefix, setname):
    """Convert MC set to MD set"""

 #debugging
 # makes debug apply only to the current thread
    #try:
        #import wingdbstub
        #if wingdbstub.debugger != None:
            #import time
            #wingdbstub.debugger.StopDebug()
            #time.sleep(1)
            #wingdbstub.debugger.StartDebug()
        #import thread
        #wingdbstub.debugger.SetDebugThreads({thread.get_ident(): 1}, default_policy=0)
        ## for V19 use
        ###    ###SpssClient._heartBeat(False)
    #except:
        #pass

    if not mcset.startswith("$"):
        raise ValueError(_("""Only an MC set can be used with this procedure"""))
    if not setname.startswith("$"):
        setname = "$" + setname    
    resolver = Resolver()
    allvars = resolver.resolve(mcset)  # check existence and get all variables
    resolver.close()

    generatedvars, generatedvalues, generatedlabels = genSetsCategoryList(mcset, allvars, resolver, setname, varprefix)
    # list new variables and labels
    StartProcedure(_("""Convert MC Set"""), "STATSMCSETCONVERT")
    table = spss.BasePivotTable(
        title=_("""Variables Generated for Set %s""") % setname,
        templateName="STATSMCSETVARS")
    table.SimplePivotTable(rowdim=_("Variable Name"),
        rowlabels=generatedvars,
        collabels=[_("Value Represented"), _("Label")],
        cells = zip(generatedvalues, generatedlabels))
    spss.EndProcedure()
    
def genSetsCategoryList(mcset, allvars, resolver, setname, varprefix):
    """Generate sorted list(s) of values with possible insertion of extra values and create SPSS macros.
    
    mcset is the mc set to convert
    allvars is the resolved list of variables in the sets
    resolver is a class that contains the MR set information from the SPSS dictionary.
    setname is the name for the output set
    varprefix is the prefix for variable names to generate"""
    

    if resolver.getSetType(mcset) != "Categories":
        raise ValueError(_("""The specified set is not a multiple category set.  Only a set of that type can be used in this procedure: %s""")
            % mcset)

    curs = spssdata.Spssdata(indexes=allvars, names=False)  # keep cases w missing, mv's set to None
    nvar = len(allvars)
    
    vvalues=set()
    for case in curs:
        for i in range(nvar):
            if not case[i] is None:   # omit sysmis and user missing values
                if resolver.getVarType(mcset) == "String":
                    val = case[i].rstrip()
                else:
                    val = case[i]
                vvalues.add(val)
    curs.CClose()
    if len(vvalues) == 0:
        raise ValueError(_("""There are no values in the set variables for set: %s""" % mcset))
    
    # copy values labels from the first variable in the set
    # MC sets are expected to have consistent value labels across variable
    # if any are defined.
    with spss.DataStep():
        valuelabels = spss.Dataset().varlist[allvars[0]].valueLabels.data

    manager = ManageValues(resolver, mcset, vvalues, setname, varprefix, valuelabels)
    manager.genData()
    manager.setgen()
    return (manager.generatednames, manager.generatedvalues, manager.generatedlabels)
    
class ManageValues(object):
    """Manage mr set values"""
    
    def __init__(self, mrsetinfo, mcset, vvalues, setname, varprefix, valuelabels):
        """mrsetinfo is the structure returned by the dataset multiResposneSet api
        Set names are always in upper case
        setname is the name for the output set
        varprefix is the prefix for the generated variables
"""
        
        attributesFromDict(locals())
        if self.mrsetinfo.getVarType(mcset) == "Numeric":
            self.valuestr = ",".join([str(item) for item in vvalues])
            self.string = False
        else:
            self.valuestr = ",".join([spssaux._smartquote(item.rstrip()) for item in vvalues])
            self.string = True
        self.setvars = self.mrsetinfo.getSetVars(mcset)
        self.generatednames = []
        self.generatedlabels = []
        self.generatedvalues = []
        
    def genData(self):
        """Generate variables holding all the dichotomies for values"""
        
        valcount = len(self.vvalues)
        computes = []
        # The VALUE function only works for numeric variables :-(
        # In ANY, all string values are considered valid.
        if self.string:
            setvars = ",".join(self.setvars)
        else:
            setvars = ",".join(["VALUE(%s)" % v for v in self.setvars])
        values = sorted(self.vvalues)
        varprefix = self.varprefix
        
        # if any generated variables already exist, they will be overwritten.
        # if they exist and are strings, the procedure will fail.
        for v in range(valcount):
            v1 = v + 1
            vname = "%(varprefix)s_%(v1)02d" % locals()
            self.generatednames.append(vname)
            val = values[v]
            vallabel = self.valuelabels.get(val, val)   # try to pick up a value label
            self.generatedvalues.append(val)
            self.generatedlabels.append(vallabel)
            if self.string:
                val = spssaux._smartquote("%s" % val)
            cmd = """COMPUTE %(vname)s = any(%(val)s, %(setvars)s).
VARIABLE LABEL %(vname)s %(vallabel)s.
VARIABLE LEVEL %(vname)s (NOMINAL).""" % locals()
            computes.append(cmd)
        spss.Submit(computes)
  
    def setgen(self):
        """construct a new MR set of the appropriate type"""
        
        cmd = """MRSETS /MDGROUP NAME=%(outputname)s LABEL="%(label)s" 
VARIABLES = %(variables)s VALUE=1
/DISPLAY NAME=[%(outputname)s]"""
        
        outputname = self.setname
        label = self.mrsetinfo.getSetLabel(self.mcset)
        variables = " ".join(self.generatednames)
        spss.Submit(cmd % locals())


 
def StartProcedure(procname, omsid):
    """Start a procedure
    
    procname is the name that will appear in the Viewer outline.  It may be translated
    omsid is the OMS procedure identifier and should not be translated.
    
    Statistics versions prior to 19 support only a single term used for both purposes.
    For those versions, the omsid will be use for the procedure name.
    
    While the spss.StartProcedure function accepts the one argument, this function
    requires both."""
    
    try:
        spss.StartProcedure(procname, omsid)
    except TypeError:  #older version
        spss.StartProcedure(omsid)
        
def attributesFromDict(d):
    """build self attributes from a dictionary d."""
    
    self = d.pop('self')
    for name, value in d.iteritems():
        setattr(self, name, value)

class Resolver(object):
    "Manage mr sets"
    
    def __init__(self):
        try:
            spss.StartDataStep()
        except:
            spss.Submit("EXECUTE.")
            spss.StartDataStep()
        self.ds = spss.Dataset()
        self.varlist = self.ds.varlist
        self.mrsets = {}
        # the api always returns the set name in upper case
        for name, theset in self.ds.multiResponseSet.data.iteritems():
            self.mrsets[name.upper()] = theset
            
    def close(self):
        try:
            spss.EndDataStep()
        except:
            pass

    def resolve(self, theset):
        """Return list of variables
        Fail if a name does not exist."""

        #When getting a multiple response set, the result is a tuple of 5 elements. The first element is the label,
        #if any, for the set. The second element specifies the variable coding--'Categories' or 'Dichotomies'. The
        #third element specifies the counted value and only applies to multiple dichotomy sets. The fourth
        #element specifies the data type--'Numeric' or 'String'. The fifth element is a list of the elementary
        #variables that define the set.
        if not theset.upper() in self.mrsets:
            raise ValueError(_("""MR set not found: %s""") % theset)
        return self.mrsets[theset.upper()][4]

    
    def getSetType(self, name):
        """Return the mr set type
        
        name is the set name to check
        return value is "Dichotomies" or "Categories" """
        
        return self.mrsets[name.upper()][1]
    
    def getVarType(self, name):
        """Return the variable type"""
        
        return self.mrsets[name.upper()][3]
    
    def getSetVars(self, name):
        """Return list of variables"""
        
        return self.mrsets[name.upper()][4]
    
    def getSetLabel(self, name):
        """Return set label"""
        
        return self.mrsets[name.upper()][0]
  
def Run(args):
    """Execute the STATS CATEGORY ORDER command"""

    args = args[args.keys()[0]]
    ###print args   #debug
    

    oobj = Syntax([
        Template("MCSET", subc="",  ktype="varname", var="mcset", islist=False),
        Template("VARPREFIX", subc="",  ktype="literal", var="varprefix"),
        Template("SETNAME", subc="", ktype="literal", var="setname", islist=False),
        Template("HELP", subc="", ktype="bool")])
    
        # ensure localization function is defined
    global _
    try:
        _("---")
    except:
        def _(msg):
            return msg

        # A HELP subcommand overrides all else
    if args.has_key("HELP"):
        #print helptext
        helper()
    else:
            processcmd(oobj, args, catvalues)

def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""
    
    import webbrowser, os.path
    
    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"
    
    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print("Help file not found:" + helpspec)
try:    #override
    from extension import helper
except:
    pass