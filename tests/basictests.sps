get file="c:\data\1991 U.S. General Social SurveywMRSets.sav".
dataset name gss.
begin program.
import spss
spss.StartDataStep()
ds = spss.Dataset()
#mrset = ds.multiResponseSet["$fredmd"]
#print mrset
mrset = ds.multiResponseSet["$fredmc"]
print mrset
spss.EndDataStep()
end program.

mrsets /display names=all.

begin program.
import STATS_MCSET_CONVERT
reload(STATS_MCSET_CONVERT)
end program.

* using gss.


compute other = RV.BERNOULLI(.3).
exec.
MRSETS
  /MDGROUP NAME=$fredmd LABEL="fred's label" CATEGORYLABELS=VARLABELS VARIABLES=hlth1 hlth2 hlth3 
    other VALUE=1
  /DISPLAY NAME=[$fredmd].
MRSETS
  /MDGROUP NAME=$sammd LABEL="sam's label" CATEGORYLABELS=VARLABELS VARIABLES=work1 work2 work3 work4 work5 work6 work7
    other VALUE=1
  /DISPLAY NAME=[$sammd].

MRSETS
  /MCGROUP NAME=$fredmc LABEL="fredmc's label" VARIABLES=hlth1 hlth2 hlth3 hlth4 hlth5 hlth6
  /DISPLAY NAME=[$fredmc].
MRSETS /DISPLAY NAME=ALL.

STATS MCSET CONVERT mcset=$fredmc varprefix=fred setname=$newmdset.

STATS MCSET CONVERT MCSET=$prob SETNAME=newset VARPREFIX=newprob.


data list fixed/color1 color2 color3(3a3).
begin data
redblugrn
redredred
blublugrn
yelpnkblk
end data.
dataset names colors.
MRSETS
  /MCGROUP NAME=$colors LABEL='rainbow' VARIABLES=color1 color2 color3
  /DISPLAY NAME=[$colors].
stats mcset convert mcset = $colors varprefix=thecolor setname=newcolors.

set mprint on.
* Custom Tables.
CTABLES
  /VLABELS VARIABLES=hlth1 DISPLAY=DEFAULT
  /TABLE hlth1 [COUNT F40.0]
  /CATEGORIES VARIABLES=hlth1[!test_hlth1] EMPTY=INCLUDE.

data list fixed/a b c (3A2).
begin data
aaaaaa
bbbbbb
aabbcc
aabbcc
end data.
variable level a b c (nominal).
value labels a b c 'aa' 'label for aa' 'bb' 'label for bb' 'cc' 'label for cc'.
dataset name strings.
exec.

DATASET ACTIVATE strings.
* Define Multiple Response Sets.
MRSETS
  /MDGROUP NAME=$abc LABEL='abc label' CATEGORYLABELS=VARLABELS VARIABLES=a b c VALUE='aa'
  /MCGROUP NAME=$abccategories VARIABLES=a b c.
