#!/bin/sh

#TARGET_STR='.*BUFFER_CAPACITY=50000'
TARGET_STR='.*LOCAL_CACHE_CAPACITY.*'
SET_BUF_CAP='3000'
#SET_BUF_CAP='4500'
echo "SET_BUF_CAP=$SET_BUF_CAP"
TARGET_STR2='CS_MODE=.'
CSMODE=1

for i in `seq 1 50`
do
	echo "./h$i/cefnetd.conf"
	echo "sed -e s/${TARGET_STR}/LOCAL_CACHE_CAPACITY=${SET_BUF_CAP}/ ./h$i/cefnetd.conf > ./h$i/tmp"
	sed -e "s/${TARGET_STR}/LOCAL_CACHE_CAPACITY=${SET_BUF_CAP}/" ./h$i/cefnetd.conf > ./h$i/tmp
	echo "mv ./h$i/tmp ./h$i/cefnetd.conf"
	mv ./h$i/tmp ./h$i/cefnetd.conf

	sed -e "s/${TARGET_STR2}/CS_MODE=${CSMODE}/" ./h$i/cefnetd.conf > ./h$i/tmp
	mv ./h$i/tmp ./h$i/cefnetd.conf

done


#TEST_STR='BUFFER_CAPACITY=30000'
#TEST_STR='#BUFFER_CAPACITY=30000'
#TEST2_STR='.BUFFER_CAPACITY=.+'
#if [ "$TEST_STR == $TEST2_STR" ]
#then
#	echo "TEST_STR == TEST2_STR !!"
#else
#	echo "TEST_STR != TEST2_STR !!"
#fi
