#!/bin/bash

## declare an array variable
declare -a arr=("http://opinew.com/"
                 "http://www.opinew.com/"
                 "https://opinew.com/"
                 "https://www.opinew.com/")

## now loop through the above array
for i in "${arr[@]}"
do
   echo "$i"
   curl -s -o /dev/null -w "%{http_code} - %{redirect_url}" "$i"
   echo -e "\n==========="
done
